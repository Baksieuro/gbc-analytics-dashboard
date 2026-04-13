"""RetailCRM v5 → upsert в Supabase public.orders."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

from dotenv import load_dotenv

from upload_mock_orders import (
    REQUEST_PAUSE_SEC,
    RetailCrmApiClient,
    _first_env,
    _normalize_base_url,
    _URL_KEYS,
    _KEY_KEYS,
    _SITE_KEYS,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DOTENV_PATH = REPO_ROOT / ".env"

_SUPABASE_URL_KEYS = ("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL", "VITE_SUPABASE_URL")
_SERVICE_ROLE_KEYS = ("SUPABASE_SERVICE_ROLE_KEY",)
_SYNC_CURRENCY_KEYS = ("SYNC_CURRENCY_CODE",)
_SYNC_KEEP_LAST_N_KEYS = ("SYNC_KEEP_LAST_N",)

CRM_PAGE_LIMIT = 50
UPSERT_BATCH_SIZE = 200
REQUEST_PAUSE_AFTER_SUPABASE_SEC = 0.2
MAX_RETRIES = 4
BACKOFF_BASE_SEC = 2.0

logger = logging.getLogger(__name__)


def _env_service_role() -> str | None:
    return _first_env(_SERVICE_ROLE_KEYS)


def _supabase_rest_base(url: str) -> str:
    return url.strip().rstrip("/") + "/rest/v1"


def _parse_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    s = str(value).strip().replace(",", ".")
    if not s:
        return Decimal("0")
    try:
        return Decimal(s)
    except InvalidOperation:
        return Decimal("0")


def _parse_ordered_at(order: Mapping[str, Any]) -> datetime:
    for key in ("createdAt", "orderDate", "statusUpdatedAt"):
        raw = order.get(key)
        if raw:
            dt = _parse_datetime_value(raw)
            if dt is not None:
                return dt
    return datetime.now(timezone.utc)


def _crm_currency_code(order: Mapping[str, Any]) -> str:
    c = order.get("currency")
    if isinstance(c, dict):
        s = str(c.get("code") or c.get("currency") or "").strip().upper()
    else:
        s = str(c or "").strip().upper()
    return s or "KZT"


def _sync_currency_override() -> str | None:
    raw = _first_env(_SYNC_CURRENCY_KEYS)
    if not raw:
        return None
    s = raw.strip().upper()
    return s[:16] if s else None


def _sync_keep_last_n() -> int | None:
    raw = _first_env(_SYNC_KEEP_LAST_N_KEYS)
    if not raw:
        return None
    try:
        n = int(raw)
    except (TypeError, ValueError):
        logger.warning("invalid SYNC_KEEP_LAST_N=%r (ignored)", raw)
        return None
    return n if n > 0 else None


def _crm_order_total(order: Mapping[str, Any]) -> Decimal:
    for key in ("totalSumm", "summ", "totalSum", "totalPrice"):
        raw = order.get(key)
        if raw is not None and str(raw).strip() != "":
            return _parse_decimal(raw)
    return Decimal("0")


def _parse_datetime_value(raw: Any) -> datetime | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if " " in text and "T" not in text:
        text = text.replace(" ", "T", 1)
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def retailcrm_order_to_row(order: Mapping[str, Any], *, include_raw: bool) -> dict[str, Any] | None:
    oid = order.get("id")
    try:
        retailcrm_id = int(oid)
    except (TypeError, ValueError):
        logger.warning("skip order: no int id")
        return None

    total = _crm_order_total(order)
    override = _sync_currency_override()
    currency = override if override else _crm_currency_code(order)
    ordered_at = _parse_ordered_at(order)
    row: dict[str, Any] = {
        "retailcrm_id": retailcrm_id,
        "total_amount": float(total.quantize(Decimal("0.01"))),
        "currency": currency[:16],
        "ordered_at": ordered_at.isoformat(),
    }
    if include_raw:
        row["raw_payload"] = dict(order) if isinstance(order, dict) else {"value": order}
    return row


def _supabase_post_json(
    url: str,
    service_key: str,
    payload: bytes,
    *,
    prefer: str,
) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": prefer,
        },
    )
    opener = urllib.request.build_opener()
    try:
        with opener.open(req, timeout=120) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.getcode() or 200, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body


def upsert_orders_batch(
    supabase_url: str,
    service_key: str,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    base = _supabase_rest_base(supabase_url)
    target = f"{base}/orders?on_conflict=retailcrm_id"
    body = json.dumps(rows, ensure_ascii=False, default=str).encode("utf-8")
    prefer = "resolution=merge-duplicates,return=minimal"
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        if attempt:
            wait = BACKOFF_BASE_SEC * (2 ** (attempt - 1))
            logger.warning("retry upsert %.1fs %s/%s", wait, attempt + 1, MAX_RETRIES)
            time.sleep(wait)
        code, resp_text = _supabase_post_json(target, service_key, body, prefer=prefer)
        if 200 <= code < 300:
            return
        if code == 429 or (500 <= code < 600):
            logger.warning("Supabase HTTP %s", code)
            last_err = RuntimeError(f"Supabase HTTP {code}")
            continue
        raise RuntimeError(f"Supabase HTTP {code}: {resp_text[:500]}")
    raise RuntimeError(f"Supabase upsert failed after {MAX_RETRIES}") from last_err


def delete_orders_not_in_ids(
    supabase_url: str,
    service_key: str,
    keep_ids: list[int],
) -> int:
    if not keep_ids:
        return 0
    ids = sorted(set(keep_ids))
    ids_csv = ",".join(str(i) for i in ids)
    base = _supabase_rest_base(supabase_url)
    target = f"{base}/orders?retailcrm_id=not.in.({ids_csv})"
    req = urllib.request.Request(
        target,
        method="DELETE",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Prefer": "return=representation",
        },
    )
    opener = urllib.request.build_opener()
    try:
        with opener.open(req, timeout=120) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if not body.strip():
                return 0
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return 0
            if isinstance(data, list):
                return len(data)
            return 0
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        raise RuntimeError(f"Supabase DELETE HTTP {e.code}: {body[:500]}") from e


def fetch_all_orders(client: RetailCrmApiClient, site: str, *, max_pages: int | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    page = 1
    while True:
        if max_pages is not None and page > max_pages:
            logger.info("stop --max-pages=%s", max_pages)
            break
        data = client.list_orders(site, page=page, limit=CRM_PAGE_LIMIT)
        if not data.get("success"):
            msg = data.get("errorMsg") or data.get("errors") or "unknown"
            raise RuntimeError(f"RetailCRM orders: {msg}")
        orders = data.get("orders")
        if not isinstance(orders, list):
            orders = []
        for o in orders:
            if isinstance(o, dict):
                out.append(o)
        pagination = data.get("pagination")
        total_page_count: int | None = None
        if isinstance(pagination, dict):
            try:
                total_page_count = int(pagination.get("totalPageCount") or 0)
            except (TypeError, ValueError):
                total_page_count = None
            try:
                cur = int(pagination.get("currentPage") or page)
            except (TypeError, ValueError):
                cur = page
            logger.info("CRM page %s/%s size=%s total=%s", cur, total_page_count or "?", len(orders), len(out))
        else:
            logger.info("CRM page %s size=%s", page, len(orders))

        if not orders:
            break
        if len(orders) < CRM_PAGE_LIMIT:
            break
        page += 1
        if REQUEST_PAUSE_SEC > 0:
            time.sleep(REQUEST_PAUSE_SEC)
    return out


def _crm_order_id(order: Mapping[str, Any]) -> int | None:
    try:
        return int(order.get("id"))
    except (TypeError, ValueError):
        return None


def fetch_orders_newer_than(
    client: RetailCrmApiClient,
    site: str,
    last_max: int,
    *,
    max_pages: int = 200,
) -> list[dict[str, Any]]:
    all_full = fetch_all_orders(client, site, max_pages=max_pages)
    return [o for o in all_full if (oid := _crm_order_id(o)) is not None and oid > last_max]


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(description="Синхронизация заказов RetailCRM → Supabase")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Ограничить число страниц CRM (для отладки)",
    )
    parser.add_argument(
        "--no-raw-payload",
        action="store_true",
        help="Не записывать raw_payload в Supabase",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только выгрузка из CRM и нормализация, без записи в Supabase",
    )
    args = parser.parse_args(argv)

    if DOTENV_PATH.is_file():
        load_dotenv(DOTENV_PATH, override=False)
    else:
        logger.warning("no .env, using process env only")

    supabase_url = _first_env(_SUPABASE_URL_KEYS)
    service_key = _env_service_role()
    if not args.dry_run:
        if not supabase_url:
            logger.error("missing SUPABASE_URL (or NEXT_PUBLIC_/VITE_ alias)")
            return 1
        if not service_key:
            logger.error("missing SUPABASE_SERVICE_ROLE_KEY")
            return 1

    base = _first_env(_URL_KEYS)
    key = _first_env(_KEY_KEYS)
    site_override = _first_env(_SITE_KEYS)
    if not base or not key:
        logger.error(
            "Задайте RETAILCRM_API_URL (или %s) и RETAILCRM_API_KEY (или %s)",
            _URL_KEYS[1],
            _KEY_KEYS[1],
        )
        return 1

    base_norm = _normalize_base_url(base)
    client = RetailCrmApiClient(base_norm, key)
    try:
        site = client.resolve_site_code(site_override)
    except Exception as e:
        logger.error("%s", e)
        return 1

    try:
        crm_orders = fetch_all_orders(client, site, max_pages=args.max_pages)
    except Exception as e:
        logger.error("RetailCRM fetch: %s", e)
        return 1

    include_raw = not args.no_raw_payload
    rows: list[dict[str, Any]] = []
    for o in crm_orders:
        row = retailcrm_order_to_row(o, include_raw=include_raw)
        if row:
            rows.append(row)

    keep_last_n = _sync_keep_last_n()
    if keep_last_n and len(rows) > keep_last_n:
        rows = sorted(rows, key=lambda r: int(r["retailcrm_id"]))[-keep_last_n:]
        logger.info("SYNC_KEEP_LAST_N=%s applied, rows limited to %s", keep_last_n, len(rows))

    logger.info("rows to upsert: %s", len(rows))
    if not crm_orders:
        logger.warning("no CRM orders site=%s (try upload_mock_orders.py)", site)
    elif not rows:
        logger.warning("CRM orders=%s normalized to 0 rows", len(crm_orders))

    if args.dry_run:
        logger.info("DRY-RUN skip Supabase")
        return 0

    try:
        for i in range(0, len(rows), UPSERT_BATCH_SIZE):
            batch = rows[i : i + UPSERT_BATCH_SIZE]
            upsert_orders_batch(supabase_url, service_key, batch)
            logger.info("upsert batch %s", len(batch))
            if REQUEST_PAUSE_AFTER_SUPABASE_SEC > 0:
                time.sleep(REQUEST_PAUSE_AFTER_SUPABASE_SEC)
        if keep_last_n:
            keep_ids = [int(r["retailcrm_id"]) for r in rows]
            deleted = delete_orders_not_in_ids(supabase_url, service_key, keep_ids)
            logger.info("prune orders outside keep-set: deleted=%s", deleted)
    except Exception as e:
        logger.error("Supabase write: %s", e)
        return 1

    logger.info("done upsert %s", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
