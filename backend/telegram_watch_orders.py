"""RetailCRM → Telegram: новые заказы выше порога, state в .telegram_orders_state.json."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from dotenv import load_dotenv

from alert_env import read_alert_min_amount_kzt
from upload_mock_orders import (
    RetailCrmApiClient,
    _first_env,
    _normalize_base_url,
    _KEY_KEYS,
    _SITE_KEYS,
    _URL_KEYS,
)
from sync_orders_to_supabase import _parse_decimal, fetch_all_orders, fetch_orders_newer_than

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parent
DOTENV_PATH = REPO_ROOT / ".env"
STATE_PATH = BACKEND_DIR / ".telegram_orders_state.json"

_TELEGRAM_TOKEN_KEYS = ("TELEGRAM_BOT_TOKEN", "API_TELEGRAM_TOKEN")
_TELEGRAM_CHAT_KEYS = ("TELEGRAM_CHAT_ID", "TELEGRAM_NAME")

logger = logging.getLogger(__name__)

_ALERT_MAX_LEN = 3900

_BAD_ITEM_TITLES = frozenset(
    {
        "",
        "noname",
        "no name",
        "-",
        "—",
        "...",
        "null",
        "none",
        "n/a",
        "na",
    }
)


def _nz(value: Any) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    return s


def _html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _href_escape(url: str) -> str:
    return url.replace("&", "&amp;").replace('"', "&quot;")


def _order_field(order: Mapping[str, Any], key: str) -> str:
    v = _nz(order.get(key))
    if v:
        return v
    c = order.get("customer")
    if isinstance(c, dict):
        v = _nz(c.get(key))
        if v:
            return v
    return ""


def _order_phone(order: Mapping[str, Any]) -> str:
    v = _nz(order.get("phone"))
    if v:
        return v
    c = order.get("customer")
    if not isinstance(c, dict):
        return ""
    v = _nz(c.get("phone"))
    if v:
        return v
    phones = c.get("phones")
    if isinstance(phones, list):
        for p in phones:
            if isinstance(p, dict):
                num = _nz(p.get("number"))
                if num:
                    return num
    return ""


def _cf_scalar(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, bool):
        return "да" if val else "нет"
    if isinstance(val, (int, float)):
        return str(val).strip()
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, dict):
        for k in ("value", "name", "text", "label", "code"):
            s = _cf_scalar(val.get(k))
            if s:
                return s
        return ""
    if isinstance(val, list):
        parts = [_cf_scalar(x) for x in val[:8]]
        return ", ".join(p for p in parts if p)
    return str(val).strip()


def _custom_fields_map(order: Mapping[str, Any]) -> dict[str, str]:
    cf = order.get("customFields")
    out: dict[str, str] = {}
    if isinstance(cf, dict):
        for k, v in cf.items():
            s = _cf_scalar(v)
            if s:
                out[str(k)] = s
        return out
    if isinstance(cf, list):
        for x in cf:
            if not isinstance(x, dict):
                continue
            code = _nz(x.get("code"))
            if not code:
                code = _nz(x.get("name"))
            if not code:
                code = _nz(x.get("fieldName"))
            fld = x.get("field")
            if not code and isinstance(fld, dict):
                code = _nz(fld.get("code") or fld.get("name"))
            s = _cf_scalar(x.get("value"))
            if not s:
                continue
            key = code or f"extra_{len(out)}"
            out[key] = s
    return out


def _merged_custom_fields(order: Mapping[str, Any]) -> dict[str, str]:
    m = dict(_custom_fields_map(order))
    cust = order.get("customer")
    if isinstance(cust, dict):
        inner = cust.get("customFields")
        if inner is not None:
            cm = _custom_fields_map({"customFields": inner})
            for k, v in cm.items():
                if k not in m or not m[k]:
                    m[k] = v
    return m


def _is_bad_item_title(s: str) -> bool:
    t = _nz(s).lower()
    return not t or t in _BAD_ITEM_TITLES


def _item_title(it: Mapping[str, Any]) -> str:
    for key in ("productName", "offerName", "name", "displayName"):
        v = _nz(it.get(key))
        if v and not _is_bad_item_title(v):
            return v
    offer = it.get("offer")
    if isinstance(offer, dict):
        for k in ("name", "displayName", "productName", "label", "article"):
            v = _nz(offer.get(k))
            if v and not _is_bad_item_title(v):
                return v
        ext_id = _nz(offer.get("externalId"))
        if ext_id and not _is_bad_item_title(ext_id):
            return ext_id
        oid = offer.get("id")
        if oid is not None and str(oid).strip():
            return f"Товар #{oid}"
    for key in ("article", "productArticle", "xmlId"):
        v = _nz(it.get(key))
        if v:
            return v
    pos_id = it.get("id")
    if pos_id is not None and str(pos_id).strip():
        return f"Позиция #{pos_id}"
    return "Позиция"


def _item_quantity(it: Mapping[str, Any]) -> str:
    q = it.get("quantity")
    if q is None:
        return "1"
    try:
        if float(q) == int(float(q)):
            return str(int(float(q)))
        return str(q).strip()
    except (TypeError, ValueError):
        return _nz(q) or "1"


def _item_price(it: Mapping[str, Any]) -> Decimal:
    for k in ("initialPrice", "purchasePrice"):
        raw = it.get(k)
        if raw is not None and str(raw).strip():
            return _parse_decimal(raw)
    prices = it.get("prices")
    if isinstance(prices, dict):
        for k in ("total", "price", "cost"):
            raw = prices.get(k)
            if raw is not None and str(raw).strip():
                return _parse_decimal(raw)
    return Decimal("0")


def _order_items_lines(order: Mapping[str, Any]) -> list[str]:
    raw = order.get("items")
    if not isinstance(raw, list) or not raw:
        return ["—"]
    lines: list[str] = []
    n = 0
    for it in raw:
        if not isinstance(it, dict):
            continue
        n += 1
        title = _item_title(it)
        qty = _item_quantity(it)
        price = _item_price(it)
        lines.append(f"{n}. {title} × {qty} — {price} KZT")
    return lines if lines else ["—"]


def _order_delivery_lines(order: Mapping[str, Any]) -> list[str]:
    d = order.get("delivery")
    if not isinstance(d, dict):
        return ["—"]
    addr = d.get("address")
    if isinstance(addr, dict):
        city = _nz(addr.get("city"))
        text = _nz(addr.get("text"))
        parts = [p for p in (city, text) if p]
        if parts:
            return [", ".join(parts)]
    data = d.get("data")
    if isinstance(data, dict):
        t = _nz(data.get("addressText") or data.get("text"))
        if t:
            return [t]
    return ["—"]


def _order_source_display(order: Mapping[str, Any]) -> str:
    src = order.get("source")
    if isinstance(src, dict):
        label = _nz(src.get("name") or src.get("label") or src.get("sourceName"))
        if label:
            return label
        code = _nz(src.get("code") or src.get("source"))
        if code:
            return code
    if isinstance(src, str) and _nz(src):
        return _nz(src)

    om = order.get("orderMethod")
    if isinstance(om, dict):
        v = _nz(om.get("name") or om.get("label"))
        if v:
            return v
    if isinstance(om, str) and _nz(om):
        return _nz(om)

    ot = order.get("orderType")
    if isinstance(ot, dict):
        v = _nz(ot.get("name") or ot.get("label"))
        if v:
            return v

    for k in ("referer", "referrer", "referralUrl"):
        v = _nz(order.get(k))
        if v:
            return v

    m = _merged_custom_fields(order)
    for key in ("utm_source", "utm_medium", "source", "istochnik", "istochnik_zakaza"):
        if key in m and m[key]:
            return m[key]
    for key, val in m.items():
        if key.startswith("extra_"):
            continue
        kl = key.lower()
        if any(x in kl for x in ("utm", "source", "источ", "реклам", "marketing")):
            return val
    raw = order.get("customFields")
    if isinstance(raw, list):
        for x in raw:
            if not isinstance(x, dict):
                continue
            meta = (
                _nz(x.get("name")) + " " + _nz(x.get("code")) + " "
                + _nz((x.get("field") or {}).get("name") if isinstance(x.get("field"), dict) else "")
                + _nz((x.get("field") or {}).get("code") if isinstance(x.get("field"), dict) else "")
            ).lower()
            if any(t in meta for t in ("utm", "source", "источ")):
                s = _cf_scalar(x.get("value"))
                if s:
                    return s
    cand = sorted(
        (i for i in m.items() if not str(i[0]).startswith("extra_")),
        key=lambda x: x[0],
    )
    if cand:
        k, v = cand[0]
        return f"{k}: {v}"
    return "—"


def _retailcrm_order_admin_url(admin_base: str, order_id: int) -> str:
    b = admin_base.strip().rstrip("/")
    if not b:
        return ""
    return f"{b}/orders/{int(order_id)}/edit"


def _normalize_telegram_chat_id(raw: str) -> str:
    s = raw.replace("\ufeff", "").strip().strip("'\"")
    s = s.strip()
    if not s:
        return s
    if s.startswith("@"):
        rest = s[1:].lstrip("@")
        return "@" + rest if rest else s
    sign = ""
    body = s
    if body.startswith("-"):
        sign = "-"
        body = body[1:]
    if body.isdigit():
        return sign + body
    uname = s.lstrip("@")
    if uname and uname[0].isalpha() and all(ch.isalnum() or ch == "_" for ch in uname):
        return "@" + uname
    return s


def _telegram_chat_id_for_json(normalized: str) -> int | str:
    if not normalized or normalized.startswith("@"):
        return normalized
    sign = ""
    b = normalized
    if b.startswith("-"):
        sign = "-"
        b = b[1:]
    if b.isdigit():
        return int(sign + b)
    return normalized


def _load_alert_currency_codes() -> frozenset[str]:
    raw = os.environ.get("ALERT_CURRENCY_CODES", "KZT,398,RUB,643")
    parts = [p.strip().upper() for p in raw.replace(";", ",").split(",") if p.strip()]
    default = frozenset({"KZT", "398", "RUB", "643"})
    return frozenset(parts) if parts else default


def _order_currency_code(order: Mapping[str, Any]) -> str:
    c = order.get("currency")
    if isinstance(c, dict):
        return str(c.get("code") or c.get("currency") or "").strip().upper()
    return str(c or "").strip().upper()


def _currency_allowed_for_alert(order: Mapping[str, Any], allowed: frozenset[str]) -> bool:
    code = _order_currency_code(order)
    if not code:
        return True
    return code in allowed


def _order_total_for_alert(order: Mapping[str, Any]) -> Decimal:
    for key in ("totalSumm", "summ", "totalSum", "totalPrice"):
        raw = order.get(key)
        if raw is not None and str(raw).strip() != "":
            return _parse_decimal(raw)
    return Decimal("0")


def _order_id(order: Mapping[str, Any]) -> int | None:
    try:
        return int(order.get("id"))
    except (TypeError, ValueError):
        return None


def _global_max_id(orders: list[dict[str, Any]]) -> int:
    m = 0
    for o in orders:
        oid = _order_id(o)
        if oid is not None and oid > m:
            m = oid
    return m


_NOTIFIED_IDS_KEY = "telegram_notified_ids"
_MAX_NOTIFIED_IDS = 5000


def _parse_notified_ids(data: Mapping[str, Any]) -> set[int]:
    raw = data.get(_NOTIFIED_IDS_KEY, data.get("notifiedOrderIds"))
    if not isinstance(raw, list):
        return set()
    out: set[int] = set()
    for x in raw:
        try:
            out.add(int(x))
        except (TypeError, ValueError):
            continue
    return out


def _load_state() -> tuple[int, set[int]]:
    if not STATE_PATH.is_file():
        return 0, set()
    try:
        with STATE_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            v = data.get("last_max_order_id", data.get("lastMaxOrderId"))
            last = int(v) if v is not None else 0
            return last, _parse_notified_ids(data)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as e:
        logger.warning("state read fail %s: %s", STATE_PATH.name, e)
    return 0, set()


def _trim_notified_ids(ids: set[int], *, keep_from_id: int) -> list[int]:
    pruned = sorted(i for i in ids if i >= keep_from_id - 1)
    if len(pruned) > _MAX_NOTIFIED_IDS:
        pruned = pruned[-_MAX_NOTIFIED_IDS:]
    return pruned


def _save_state(last_max_order_id: int, notified_ids: set[int], *, watermark_floor: int) -> None:
    listed = _trim_notified_ids(notified_ids, keep_from_id=watermark_floor)
    payload = {"last_max_order_id": last_max_order_id, _NOTIFIED_IDS_KEY: listed}
    tmp = STATE_PATH.with_suffix(".tmp")
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    tmp.write_text(text + "\n", encoding="utf-8")
    tmp.replace(STATE_PATH)


def _should_alert(order: Mapping[str, Any], threshold: Decimal, currencies: frozenset[str]) -> bool:
    if not _currency_allowed_for_alert(order, currencies):
        return False
    total = _order_total_for_alert(order)
    return total > threshold


def _safe_watermark_contiguous(
    last_max: int,
    new_orders: list[dict[str, Any]],
    threshold: Decimal,
    currencies: frozenset[str],
    notified_ids: set[int],
) -> int:
    safe = last_max
    for o in sorted(new_orders, key=lambda x: _order_id(x) or 0):
        oid = _order_id(o)
        if oid is None or oid <= last_max:
            continue
        if not _should_alert(o, threshold, currencies):
            safe = oid
        elif oid in notified_ids:
            safe = oid
        else:
            break
    return safe


def _build_alert_message_html(order: Mapping[str, Any], *, admin_base: str) -> str:
    e = _html_escape
    oid = _order_id(order)
    ext = _nz(order.get("externalId"))
    total = _order_total_for_alert(order)
    fn = _order_field(order, "firstName")
    ln = _order_field(order, "lastName")
    name = " ".join(x for x in (fn, ln) if x).strip() or "—"
    phone = _order_phone(order) or "—"
    email = _order_field(order, "email") or "—"
    source = _order_source_display(order)

    blocks: list[str] = [
        "<b>" + e("RetailCRM: Крупный заказ") + "</b>",
        "",
        e("Сумма: ") + "<b>" + e(str(total)) + " KZT</b>",
        "",
        "<b>" + e("Данные клиента") + "</b>",
        e("Имя, фамилия: ") + e(name),
        e("Номер телефона: ") + e(phone),
        e("Почта: ") + e(email),
        "",
        "<b>" + e("Содержимое заказа") + "</b>",
        *[e(line) for line in _order_items_lines(order)],
        "",
        "<b>" + e("Доставка") + "</b>",
        *[e(line) for line in _order_delivery_lines(order)],
        "",
        "<b>" + e("Источник") + "</b>",
        e(source),
    ]
    crm_url = _retailcrm_order_admin_url(admin_base, oid) if oid is not None else ""
    blocks.append("")
    if crm_url:
        he = _href_escape(crm_url)
        blocks.append('<a href="' + he + '">' + e("Открыть в RetailCRM") + "</a>")
    else:
        blocks.append(e("Ссылка: задайте RETAILCRM_API_URL в .env"))
    if oid is not None or ext:
        tail = f"id: {oid}" if oid is not None else ""
        if ext:
            tail = f"{tail} · {ext}" if tail else ext
        blocks.append("")
        blocks.append("<code>" + e(tail) + "</code>")

    text = "\n".join(blocks)
    if len(text) > _ALERT_MAX_LEN:
        text = text[: _ALERT_MAX_LEN - 5] + "\n…"
    return text


def send_telegram_message(
    *,
    token: str,
    chat_id: str,
    text: str,
    timeout_sec: float = 30.0,
    parse_mode: str | None = None,
) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    norm = _normalize_telegram_chat_id(chat_id)
    cid = _telegram_chat_id_for_json(norm)
    payload: dict[str, Any] = {
        "chat_id": cid,
        "text": text,
        "disable_web_page_preview": True,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json; charset=UTF-8"},
    )
    opener = urllib.request.build_opener()
    try:
        with opener.open(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        tail = err_body[:200]
        if e.code == 400 and "chat not found" in err_body.lower():
            tail += " | id: /start боту, группа: отриц. id, канал: @name"
        raise RuntimeError(f"Telegram HTTP {e.code} {tail}") from None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError("Telegram: bad JSON") from e
    if not data.get("ok"):
        desc = data.get("description") or data
        raise RuntimeError(f"Telegram sendMessage: {desc}")


def run_once() -> int:
    token = _first_env(_TELEGRAM_TOKEN_KEYS)
    chat_raw = _first_env(_TELEGRAM_CHAT_KEYS)
    chat_id = _normalize_telegram_chat_id(str(chat_raw or ""))
    if not token or not chat_id:
        logger.error(
            "Задайте TELEGRAM_BOT_TOKEN (или %s) и TELEGRAM_CHAT_ID (или %s)",
            _TELEGRAM_TOKEN_KEYS[1],
            _TELEGRAM_CHAT_KEYS[1],
        )
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

    try:
        threshold = Decimal(read_alert_min_amount_kzt())
    except ValueError as e:
        logger.error("%s", e)
        return 1
    currencies = _load_alert_currency_codes()
    logger.info("threshold=%s currencies=%s", threshold, ",".join(sorted(currencies)))
    base_norm = _normalize_base_url(base)
    if "help.retailcrm" in base_norm.lower():
        logger.warning("RETAILCRM URL looks like docs, use *.retailcrm.ru host")

    client = RetailCrmApiClient(base_norm, key)
    try:
        site = client.resolve_site_code(site_override)
    except Exception as e:
        logger.error("%s", e)
        return 1

    state_existed = STATE_PATH.is_file()
    last_max, notified_ids = _load_state()
    watermark_start = last_max

    try:
        if not state_existed:
            orders = fetch_all_orders(client, site, max_pages=None)
        else:
            orders = fetch_orders_newer_than(client, site, last_max, max_pages=200)
    except Exception as e:
        logger.error("RetailCRM fetch: %s", e)
        return 1

    if not state_existed:
        global_init = max(last_max, _global_max_id(orders))
        _save_state(global_init, set(), watermark_floor=global_init)
        logger.info("init watermark last_max_order_id=%s no notify", global_init)
        return 0

    new_orders = [o for o in orders if (oid := _order_id(o)) is not None and oid > last_max]
    try:
        probe_n = max(0, min(200, int(os.environ.get("TELEGRAM_ORDER_ID_PROBE", "40"))))
    except ValueError:
        probe_n = 40
    seen_ids: set[int] = {x for x in (_order_id(o) for o in new_orders) if x is not None}
    for oid in range(last_max + 1, last_max + 1 + probe_n):
        if oid in seen_ids:
            continue
        got = client.get_order(site, oid)
        if got and _order_id(got) == oid:
            new_orders.append(got)
            seen_ids.add(oid)
            logger.info("probe GET id=%s", oid)

    new_orders.sort(key=lambda o: _order_id(o) or 0)
    global_max = max(last_max, _global_max_id(orders), _global_max_id(new_orders))
    logger.info(
        "site=%s fetched=%s watermark=%s crm_max=%s new_count=%s",
        site,
        len(orders),
        last_max,
        global_max,
        len(new_orders),
    )
    if not new_orders:
        logger.info(
            "no new orders probe=%s..%s site=%s watermark=%s",
            last_max + 1,
            last_max + probe_n,
            site,
            last_max,
        )

    eligible_orders = [o for o in new_orders if _should_alert(o, threshold, currencies)]
    pending_notify = [
        o for o in eligible_orders if _order_id(o) is None or _order_id(o) not in notified_ids
    ]
    had_error = False
    alerted = 0
    for o in pending_notify:
        oid = _order_id(o)
        text = _build_alert_message_html(o, admin_base=base_norm)
        try:
            send_telegram_message(
                token=token, chat_id=chat_id, text=text, parse_mode="HTML"
            )
            alerted += 1
            if oid is not None:
                notified_ids.add(oid)
                _save_state(watermark_start, notified_ids, watermark_floor=watermark_start)
            logger.info("sent id=%s", o.get("id"))
        except Exception as e:
            logger.error("telegram fail id=%s: %s", o.get("id"), e)
            had_error = True

    if new_orders and alerted == 0:
        if pending_notify:
            logger.warning("pending=%s send failed", len(pending_notify))
        elif eligible_orders:
            logger.info("eligible=%s already notified", len(eligible_orders))
        else:
            o0 = new_orders[0]
            tot0 = _order_total_for_alert(o0)
            logger.warning(
                "new=%s none pass filter thr=%s cur=%s total=%s",
                len(new_orders),
                threshold,
                _order_currency_code(o0),
                tot0,
            )

    safe_wm = _safe_watermark_contiguous(
        last_max, new_orders, threshold, currencies, notified_ids
    )
    _save_state(safe_wm, notified_ids, watermark_floor=safe_wm)
    if safe_wm != last_max:
        logger.info("watermark %s -> %s", last_max, safe_wm)

    return 1 if had_error else 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(description="RetailCRM - Telegram при заказе > порога KZT")
    parser.add_argument(
        "--loop",
        nargs="?",
        const=300,
        type=int,
        metavar="SEC",
        help="Повторять каждые SEC секунд (по умолчанию 300)",
    )
    args = parser.parse_args(argv)

    if DOTENV_PATH.is_file():
        load_dotenv(DOTENV_PATH, override=False)
    else:
        logger.warning("no .env, using process env only")

    if args.loop is None:
        return run_once()

    interval = max(5, int(args.loop))
    logger.info("loop interval=%ss", interval)
    while True:
        code = run_once()
        if code != 0:
            logger.warning("run_once exit=%s", code)
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
