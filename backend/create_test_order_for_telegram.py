"""Тестовый заказ в CRM; полная цепочка: --pipeline."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from alert_env import read_alert_min_amount_kzt
from upload_mock_orders import (
    DOTENV_PATH,
    mock_order_to_retailcrm_payload,
    resolve_order_catalog_for_upsert,
    retailcrm_client_and_site_from_env,
    upsert_one,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parent
STATE_PATH = BACKEND_DIR / ".telegram_orders_state.json"


def _minimal_row(amount: float) -> dict[str, Any]:
    return {
        "firstName": "Айгуль",
        "lastName": "Касымова",
        "phone": "+77001234501",
        "email": "aigul.kasymova@example.com",
        "currency": "KZT",
        "countryIso": "KZ",
        "orderType": "eshop-individual",
        "orderMethod": "shopping-cart",
        "status": "new",
        "items": [
            {
                "productName": "Корректирующее бельё Nova Classic",
                "quantity": 1,
                "initialPrice": amount,
            }
        ],
        "delivery": {
            "address": {
                "city": "Алматы",
                "text": "ул. Абая 150, кв 12",
            }
        },
        "customFields": {
            "utm_source": "telegram-test",
        },
    }


def _default_amount_above_threshold() -> float:
    try:
        t = read_alert_min_amount_kzt()
        base = float(max(t + 1, 60000))
    except ValueError:
        base = 60000.0
    jitter = float((time.time_ns() % 8999) + 1)
    return base + jitter


def _run_backend_script(rel_name: str) -> int:
    script = BACKEND_DIR / rel_name
    return subprocess.call([sys.executable, str(script)], cwd=str(REPO_ROOT))


def _create_one_order(amount: float) -> int:
    pair = retailcrm_client_and_site_from_env()
    if pair is None:
        return 1
    client, site = pair

    row = _minimal_row(amount)
    mock_ot = str(row.get("orderType") or "")
    mock_om = str(row.get("orderMethod") or "")
    r_type, r_method, omit_method_fallback = resolve_order_catalog_for_upsert(
        client,
        mock_order_type=mock_ot,
        mock_order_method=mock_om,
    )
    if not r_type:
        logger.error("set RETAILCRM_ORDER_TYPE_CODE or fix order-types catalog")
        return 1

    external_id = f"gbc-tg-test-{int(time.time())}"
    order = mock_order_to_retailcrm_payload(
        external_id,
        row,
        order_type_code=r_type,
        order_method_code=r_method,
        omit_order_method=omit_method_fallback,
    )

    try:
        action, resp = upsert_one(client, site, order)
    except Exception as e:
        logger.exception("create order: %s", e)
        return 1

    if action == "error":
        err = str(resp.get("errorMsg") or "")
        logger.error("CRM reject: %s", err[:300])
        return 1

    rid = resp.get("id")
    ord_obj = resp.get("order")
    if rid is None and isinstance(ord_obj, dict):
        rid = ord_obj.get("id")
    logger.info("%s externalId=%s id=%s", action, external_id, rid)
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Тестовый заказ в RetailCRM для проверки алерта в Telegram",
    )
    parser.add_argument(
        "--amount",
        type=float,
        default=None,
        help="Сумма строки, ₸. По умолчанию: выше порога + случайное 1..8999 ₸",
    )
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="watermark (if needed) → order → sync → watcher",
    )
    parser.add_argument(
        "--run-watcher",
        action="store_true",
        help="run telegram_watch_orders.py once after create",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if DOTENV_PATH.is_file():
        load_dotenv(DOTENV_PATH, override=False)
    else:
        logger.warning("no .env")

    amount = args.amount if args.amount is not None else _default_amount_above_threshold()
    logger.info("order line amount=%s KZT", amount)

    if args.pipeline and not STATE_PATH.is_file():
        logger.info("no %s: init watcher (watermark only)", STATE_PATH.name)
        rc = _run_backend_script("telegram_watch_orders.py")
        if rc != 0:
            return rc

    rc = _create_one_order(amount)
    if rc:
        return rc

    if args.pipeline:
        logger.info("sync → Supabase")
        rc = _run_backend_script("sync_orders_to_supabase.py")
        if rc != 0:
            return rc
        logger.info("watcher run")
        return _run_backend_script("telegram_watch_orders.py")

    if args.run_watcher:
        return _run_backend_script("telegram_watch_orders.py")

    logger.info("next: sync + watcher or use --pipeline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
