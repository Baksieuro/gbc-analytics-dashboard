"""Загрузка mock_orders.json в RetailCRM API v5."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Mapping

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
MOCK_PATH = REPO_ROOT / "mock_orders.json"
DOTENV_PATH = REPO_ROOT / ".env"

_URL_KEYS = ("RETAILCRM_API_URL", "API_RETAIL_URL_METHODS")
_KEY_KEYS = ("RETAILCRM_API_KEY", "API_RETAIL_TOKEN")
_SITE_KEYS = ("RETAILCRM_SITE",)
_ORDER_TYPE_KEYS = ("RETAILCRM_ORDER_TYPE_CODE",)
_ORDER_METHOD_KEYS = ("RETAILCRM_ORDER_METHOD_CODE",)

REQUEST_PAUSE_SEC = 0.35
MAX_RETRIES = 4
BACKOFF_BASE_SEC = 2.0

logger = logging.getLogger(__name__)


def _env_nonempty(name: str) -> str | None:
    v = os.environ.get(name)
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _first_env(names: tuple[str, ...]) -> str | None:
    for n in names:
        val = _env_nonempty(n)
        if val is not None:
            return val
    return None


def _normalize_base_url(url: str) -> str:
    u = url.strip().rstrip("/")
    suffix = "/api/v5"
    if u.lower().endswith(suffix):
        u = u[: -len(suffix)].rstrip("/")
    return u


def _strip_none_shallow(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def mock_order_to_retailcrm_payload(
    external_id: str,
    row: Mapping[str, Any],
    *,
    order_type_code: str | None = None,
    order_method_code: str | None = None,
    omit_order_method: bool = False,
) -> dict[str, Any]:
    items_raw = row.get("items") or []
    items: list[dict[str, Any]] = []
    for idx, it in enumerate(items_raw):
        if not isinstance(it, dict):
            continue
        name = (str(it.get("productName") or "")).strip() or f"item-{idx + 1}"
        qty = int(it.get("quantity") or 1)
        price = it.get("initialPrice")
        try:
            price_f = float(price) if price is not None else 0.0
        except (TypeError, ValueError):
            price_f = 0.0
        items.append(
            {
                "offer": {"name": name, "displayName": name},
                "quantity": max(1, qty),
                "initialPrice": price_f,
            }
        )

    delivery_block: dict[str, Any] | None = None
    delivery = row.get("delivery")
    if isinstance(delivery, dict):
        addr = delivery.get("address")
        if isinstance(addr, dict):
            addr_out = _strip_none_shallow(
                {
                    "city": addr.get("city"),
                    "text": addr.get("text"),
                }
            )
            if addr_out:
                delivery_block = {"address": addr_out}

    eff_type = order_type_code if order_type_code is not None else row.get("orderType")
    if order_method_code is not None:
        eff_method: str | None = order_method_code
    elif omit_order_method:
        eff_method = None
    else:
        eff_method = row.get("orderMethod")

    cur = str(row.get("currency") or "KZT").strip().upper() or "KZT"
    order: dict[str, Any] = {
        "externalId": external_id,
        "firstName": row.get("firstName"),
        "lastName": row.get("lastName"),
        "phone": row.get("phone"),
        "email": row.get("email"),
        "orderType": eff_type,
        "orderMethod": eff_method,
        "status": row.get("status"),
        "currency": cur,
        "countryIso": str(row.get("countryIso") or "KZ").strip().upper() or "KZ",
        "items": items,
    }
    if delivery_block:
        order["delivery"] = delivery_block

    cf = row.get("customFields")
    if isinstance(cf, dict) and cf:
        order["customFields"] = cf

    return _strip_none_shallow(order)


def _looks_like_duplicate_external_id(msg: str) -> bool:
    m = msg.lower()
    if "существ" in m or "дубл" in m:
        return True
    if "external" in m and ("exist" in m or "already" in m or "duplicate" in m):
        return True
    if "already exists" in m:
        return True
    return False


def resolve_catalog_code(
    label: str,
    entries: list[dict[str, Any]],
    *,
    env_code: str | None,
    mock_code: str | None,
    required: bool = True,
) -> str | None:
    if not entries:
        if env_code:
            logger.info("%s: empty catalog, use .env %s", label, env_code)
            return env_code
        if required:
            logger.error("%s: empty catalog, no .env code", label)
        return None

    codes = [str(e["code"]) for e in entries if isinstance(e, dict) and e.get("code")]
    if env_code:
        if env_code in codes:
            logger.info("%s: .env %s", label, env_code)
            return env_code
        logger.warning("%s: .env code %s not in CRM (%s codes)", label, env_code, len(codes))
    if mock_code and str(mock_code) in codes:
        return str(mock_code)
    for e in entries:
        if not isinstance(e, dict):
            continue
        if e.get("active") is False:
            continue
        c = e.get("code")
        if c:
            if mock_code:
                logger.info("%s: mock %s missing, use %s", label, mock_code, c)
            return str(c)
    for e in entries:
        if isinstance(e, dict) and e.get("code"):
            c = str(e["code"])
            logger.info("%s: fallback code %s", label, c)
            return c
    if required:
        logger.error("%s: no code", label)
    return None


def _flatten_errors(errors: Any) -> str:
    if not errors:
        return ""
    if isinstance(errors, str):
        return errors
    if isinstance(errors, dict):
        parts: list[str] = []
        for v in errors.values():
            if isinstance(v, str):
                parts.append(v)
            elif isinstance(v, list):
                parts.extend(str(x) for x in v)
            else:
                parts.append(str(v))
        return " ".join(parts)
    return str(errors)


class RetailCrmApiClient:
    def __init__(self, base_url: str, api_key: str, pause_sec: float = REQUEST_PAUSE_SEC) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.pause_sec = pause_sec
        self._opener = urllib.request.build_opener()

    def _sleep_rate_limit(self) -> None:
        if self.pause_sec > 0:
            time.sleep(self.pause_sec)

    def _request_json(
        self,
        method: str,
        path_under_v5: str,
        *,
        query: dict[str, str] | None = None,
        form: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        q: dict[str, str] = {"apiKey": self.api_key}
        if query:
            q.update(query)
        qs = urllib.parse.urlencode(q, doseq=True)
        url = f"{self.base_url}/api/v5/{path_under_v5.lstrip('/')}?{qs}"
        last_err: Exception | None = None
        for attempt in range(MAX_RETRIES):
            self._sleep_rate_limit()
            data_bytes: bytes | None = None
            headers: dict[str, str] = {}
            if form is not None:
                data_bytes = urllib.parse.urlencode(form).encode("utf-8")
                headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
            req = urllib.request.Request(url, data=data_bytes, method=method, headers=headers)
            try:
                with self._opener.open(req, timeout=90) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace") if e.fp else ""
                if e.code == 429 or (500 <= e.code < 600):
                    wait = BACKOFF_BASE_SEC * (2**attempt)
                    logger.warning("HTTP %s retry %.1fs %s/%s", e.code, wait, attempt + 1, MAX_RETRIES)
                    time.sleep(wait)
                    last_err = e
                    continue
                try:
                    return json.loads(body) if body else {"success": False, "errorMsg": body}
                except json.JSONDecodeError:
                    raise RuntimeError(
                        f"RetailCRM HTTP {e.code}: not JSON (check base URL, key, RETAILCRM_SITE)"
                    ) from None
            except urllib.error.URLError as e:
                wait = BACKOFF_BASE_SEC * (2**attempt)
                logger.warning("network %s retry %.1fs", e.reason, wait)
                time.sleep(wait)
                last_err = e
                continue
            try:
                return json.loads(raw)
            except json.JSONDecodeError as e:
                raise RuntimeError("RetailCRM: bad JSON") from e
        raise RuntimeError(f"RetailCRM: failed after {MAX_RETRIES}") from last_err

    def get_sites(self) -> list[dict[str, Any]]:
        data = self._request_json("GET", "reference/sites")
        if not data.get("success"):
            msg = data.get("errorMsg") or data.get("errors") or "unknown"
            raise RuntimeError(f"reference/sites: {msg}")
        sites = data.get("sites")
        if not isinstance(sites, list):
            return []
        return [s for s in sites if isinstance(s, dict)]

    def reference_order_types(self) -> list[dict[str, Any]]:
        data = self._request_json("GET", "reference/order-types")
        if not data.get("success"):
            msg = data.get("errorMsg") or data.get("errors") or "unknown"
            raise RuntimeError(f"reference/order-types: {msg}")
        arr = data.get("orderTypes")
        if not isinstance(arr, list):
            return []
        return [x for x in arr if isinstance(x, dict)]

    def reference_order_methods(self) -> list[dict[str, Any]]:
        data = self._request_json("GET", "reference/order-methods")
        if not data.get("success"):
            msg = data.get("errorMsg") or data.get("errors") or "unknown"
            raise RuntimeError(f"reference/order-methods: {msg}")
        arr = data.get("orderMethods")
        if not isinstance(arr, list):
            return []
        return [x for x in arr if isinstance(x, dict)]

    def resolve_site_code(self, forced: str | None) -> str:
        if forced:
            return forced
        sites = self.get_sites()
        if not sites:
            raise RuntimeError("reference/sites empty: set RETAILCRM_SITE in .env")
        code = sites[0].get("code")
        if not code:
            raise RuntimeError("site has no code in API response")
        logger.info("default site %s", code)
        return str(code)

    def create_order(self, site: str, order: dict[str, Any]) -> dict[str, Any]:
        form = {"site": site, "order": json.dumps(order, ensure_ascii=False)}
        return self._request_json("POST", "orders/create", form=form)

    def edit_order_by_external_id(self, site: str, external_id: str, order: dict[str, Any]) -> dict[str, Any]:
        enc = urllib.parse.quote(str(external_id), safe="")
        form = {
            "site": site,
            "order": json.dumps(order, ensure_ascii=False),
            "by": "externalId",
        }
        return self._request_json("POST", f"orders/{enc}/edit", form=form)

    def get_order(self, site: str, order_id: int) -> dict[str, Any] | None:
        enc = urllib.parse.quote(str(int(order_id)), safe="")
        data = self._request_json("GET", f"orders/{enc}", query={"site": site})
        if not data.get("success"):
            return None
        order = data.get("order")
        return order if isinstance(order, dict) else None

    def list_orders(
        self,
        site: str,
        *,
        page: int = 1,
        limit: int = 100,
    ) -> dict[str, Any]:
        query: dict[str, str] = {
            "site": site,
            "page": str(max(1, page)),
            "limit": str(max(1, min(limit, 100))),
        }
        return self._request_json("GET", "orders", query=query)


def upsert_one(
    client: RetailCrmApiClient,
    site: str,
    order: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    ext = str(order.get("externalId") or "")
    created = client.create_order(site, order)
    if created.get("success"):
        return "created", created
    err_msg = str(created.get("errorMsg") or "")
    err_flat = _flatten_errors(created.get("errors"))
    combined = f"{err_msg} {err_flat}".strip()
    if _looks_like_duplicate_external_id(combined):
        logger.info("%s exists, edit", ext)
        edited = client.edit_order_by_external_id(site, ext, order)
        if edited.get("success"):
            return "updated", edited
        return "error", edited
    logger.error("create fail %s: %s", ext, combined or "(empty)")
    return "error", created


def load_project_dotenv() -> None:
    if DOTENV_PATH.is_file():
        load_dotenv(DOTENV_PATH, override=False)
    else:
        logger.warning("no .env, using process env only")


def retailcrm_client_and_site_from_env() -> tuple[RetailCrmApiClient, str] | None:
    base = _first_env(_URL_KEYS)
    key = _first_env(_KEY_KEYS)
    site_override = _first_env(_SITE_KEYS)
    if not base or not key:
        logger.error(
            "Задайте RETAILCRM_API_URL (или %s) и RETAILCRM_API_KEY (или %s)",
            _URL_KEYS[1],
            _KEY_KEYS[1],
        )
        return None
    base_norm = _normalize_base_url(base)
    if "help.retailcrm" in base_norm.lower():
        logger.warning("RETAILCRM URL looks like docs, use account host *.retailcrm.ru")
    client = RetailCrmApiClient(base_norm, key)
    try:
        site = client.resolve_site_code(site_override)
    except Exception as e:
        logger.error("%s", e)
        return None
    return client, site


def resolve_order_catalog_for_upsert(
    client: RetailCrmApiClient,
    *,
    mock_order_type: str | None,
    mock_order_method: str | None,
) -> tuple[str | None, str | None, bool]:
    try:
        ot_entries = client.reference_order_types()
    except Exception as e:
        logger.error("%s", e)
        return None, None, False
    try:
        om_entries = client.reference_order_methods()
    except Exception as e:
        logger.warning("reference/order-methods: %s", e)
        om_entries = []

    r_type = resolve_catalog_code(
        "Тип заказа",
        ot_entries,
        env_code=_first_env(_ORDER_TYPE_KEYS),
        mock_code=mock_order_type,
        required=True,
    )
    r_method = resolve_catalog_code(
        "Способ оформления",
        om_entries,
        env_code=_first_env(_ORDER_METHOD_KEYS),
        mock_code=mock_order_method,
        required=False,
    )
    omit_method_fallback = len(om_entries) == 0
    return r_type, r_method, omit_method_fallback


def load_mock_orders(limit: int) -> list[dict[str, Any]]:
    if not MOCK_PATH.is_file():
        raise FileNotFoundError(str(MOCK_PATH))
    with MOCK_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("mock_orders.json must be a JSON array")
    out: list[dict[str, Any]] = []
    for row in data[:limit]:
        if isinstance(row, dict):
            out.append(row)
    return out


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(description="Загрузка mock_orders.json в RetailCRM")
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Сколько заказов взять с начала файла (по умолчанию 50)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только проверить конфиг и маппинг, без HTTP к CRM",
    )
    args = parser.parse_args(argv)

    load_project_dotenv()

    if args.dry_run:
        rows = load_mock_orders(args.limit)
        for i, row in enumerate(rows):
            ext = f"gbc-mock-{i + 1:03d}"
            payload = mock_order_to_retailcrm_payload(ext, row)
            logger.info("DRY-RUN %s items=%s", ext, len(payload.get("items") or []))
        logger.info("DRY-RUN OK, заказов: %s", len(rows))
        return 0

    pair = retailcrm_client_and_site_from_env()
    if pair is None:
        return 1
    client, site = pair

    rows = load_mock_orders(args.limit)
    if not rows:
        logger.error("no orders to upload")
        return 1

    first_row = rows[0]
    mock_ot_s = str(first_row["orderType"]) if isinstance(first_row.get("orderType"), str) else None
    mock_om_s = str(first_row["orderMethod"]) if isinstance(first_row.get("orderMethod"), str) else None

    r_type, r_method, omit_method_fallback = resolve_order_catalog_for_upsert(
        client,
        mock_order_type=mock_ot_s,
        mock_order_method=mock_om_s,
    )

    if not r_type:
        logger.error("orderType unresolved: set RETAILCRM_ORDER_TYPE_CODE in .env")
        return 1

    if omit_method_fallback and not r_method:
        logger.info("empty order-methods, skip orderMethod from mock")
    logger.info("upload orderType=%s orderMethod=%s", r_type, r_method or "-")

    ok = 0
    fail = 0
    for i, row in enumerate(rows):
        ext = f"gbc-mock-{i + 1:03d}"
        order = mock_order_to_retailcrm_payload(
            ext,
            row,
            order_type_code=r_type,
            order_method_code=r_method,
            omit_order_method=omit_method_fallback,
        )
        try:
            action, resp = upsert_one(client, site, order)
        except Exception as e:
            logger.exception("order %s: %s", ext, e)
            fail += 1
            continue
        if action == "error":
            fail += 1
            err_msg = str(resp.get("errorMsg") or "")
            err_flat = _flatten_errors(resp.get("errors"))
            tail = f"{err_msg} {err_flat}".strip()
            logger.error("API %s: %s", ext, tail or "(no error text)")
            continue
        ok += 1
        rid = resp.get("id")
        ord_obj = resp.get("order")
        if rid is None and isinstance(ord_obj, dict):
            rid = ord_obj.get("id")
        logger.info("%s %s id=%s", action.upper(), ext, rid)

    logger.info("done ok=%s fail=%s", ok, fail)
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
