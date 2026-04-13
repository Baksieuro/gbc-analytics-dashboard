"""Порог алерта TASK-2: сумма заказа и условие строго > threshold (telegram_watch_orders)."""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_backend = str(_REPO_ROOT / "backend")
if _backend not in sys.path:
    sys.path.insert(0, _backend)

import telegram_watch_orders as tw  # noqa: E402

from telegram_watch_orders import (  # noqa: E402
    _build_alert_message_html,
    _custom_fields_map,
    _item_title,
    _merged_custom_fields,
    _normalize_telegram_chat_id,
    _order_source_display,
    _order_total_for_alert,
    _safe_watermark_contiguous,
    _should_alert,
    _telegram_chat_id_for_json,
    send_telegram_message,
)

_DEFAULT_CURRENCIES = frozenset({"KZT", "398", "RUB", "643"})


@pytest.mark.parametrize(
    ("order", "expected"),
    [
        ({"totalSumm": "100.5"}, Decimal("100.5")),
        ({"summ": "200"}, Decimal("200")),
        ({"totalSum": "50"}, Decimal("50")),
        ({"totalPrice": "10"}, Decimal("10")),
        ({}, Decimal("0")),
        ({"totalSumm": "", "summ": "7"}, Decimal("7")),
        ({"totalSumm": "  1.25  "}, Decimal("1.25")),
    ],
)
def test_order_total_for_alert(order: dict, expected: Decimal) -> None:
    assert _order_total_for_alert(order) == expected


def test_order_total_prefers_first_non_empty_key() -> None:
    order = {"totalSumm": "1", "summ": "999"}
    assert _order_total_for_alert(order) == Decimal("1")


@pytest.mark.parametrize(
    ("total_str", "threshold", "want_alert"),
    [
        ("100000", Decimal("100000"), False),
        ("100000.00", Decimal("100000"), False),
        ("100000.01", Decimal("100000"), True),
        ("99999.99", Decimal("100000"), False),
    ],
)
def test_should_alert_strict_gt_threshold(
    total_str: str, threshold: Decimal, want_alert: bool
) -> None:
    order = {"id": 1, "totalSumm": total_str, "currency": "KZT"}
    assert _should_alert(order, threshold, _DEFAULT_CURRENCIES) is want_alert


def test_should_alert_at_threshold_plus_minimal_epsilon() -> None:
    threshold = Decimal("750000")
    epsilon = Decimal("0.01")
    at = {"id": 2, "totalSumm": str(threshold), "currency": "KZT"}
    above = {"id": 3, "totalSumm": str(threshold + epsilon), "currency": "KZT"}
    assert _should_alert(at, threshold, _DEFAULT_CURRENCIES) is False
    assert _should_alert(above, threshold, _DEFAULT_CURRENCIES) is True


def test_should_alert_false_when_currency_not_allowed() -> None:
    order = {"id": 4, "totalSumm": "999999999", "currency": "USD"}
    assert _should_alert(order, Decimal("1"), _DEFAULT_CURRENCIES) is False


def test_send_telegram_message_no_real_http() -> None:
    ok_body = json.dumps({"ok": True}, ensure_ascii=False).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = ok_body
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_resp
    mock_ctx.__exit__.return_value = None
    mock_opener = MagicMock()
    mock_opener.open.return_value = mock_ctx

    with patch("telegram_watch_orders.urllib.request.build_opener", return_value=mock_opener):
        send_telegram_message(token="dummy", chat_id='"12345"', text="ping", timeout_sec=5.0)

    mock_opener.open.assert_called_once()
    req = mock_opener.open.call_args[0][0]
    assert req.full_url.startswith("https://api.telegram.org/botdummy/sendMessage")
    assert req.method == "POST"
    payload = json.loads(req.data.decode("utf-8"))
    assert payload["chat_id"] == 12345
    assert payload["text"] == "ping"


@pytest.mark.parametrize(
    ("raw", "want_norm", "want_json"),
    [
        ('"987"', "987", 987),
        ("  -10012  ", "-10012", -10012),
        ("@mychan", "@mychan", "@mychan"),
        ("mychan", "@mychan", "@mychan"),
        ("\ufeff42", "42", 42),
    ],
)
def test_normalize_telegram_chat_id(raw: str, want_norm: str, want_json: int | str) -> None:
    n = _normalize_telegram_chat_id(raw)
    assert n == want_norm
    assert _telegram_chat_id_for_json(n) == want_json


def test_build_alert_message_html_mock_like_order() -> None:
    order = {
        "id": 121,
        "externalId": "gbc-tg-test-1",
        "totalSumm": "62685",
        "currency": "KZT",
        "firstName": "Айгуль",
        "lastName": "Касымова",
        "phone": "+77001234501",
        "email": "aigul.kasymova@example.com",
        "items": [
            {
                "productName": "Корректирующее бельё Nova Classic",
                "quantity": 1,
                "initialPrice": 62685,
            }
        ],
        "delivery": {
            "address": {"city": "Алматы", "text": "ул. Абая 150, кв 12"},
        },
        "customFields": {"utm_source": "instagram"},
    }
    text = _build_alert_message_html(order, admin_base="https://demo.retailcrm.ru")
    assert "<b>" in text
    assert "RetailCRM: Крупный заказ" in text
    assert "62685 KZT" in text
    assert "Айгуль" in text and "Касымова" in text
    assert "+77001234501" in text
    assert "aigul.kasymova@example.com" in text
    assert "Корректирующее бельё Nova Classic" in text
    assert "Алматы" in text and "Абая" in text
    assert "instagram" in text
    assert 'href="https://demo.retailcrm.ru/orders/121/edit"' in text
    assert "gbc-tg-test-1" in text


def test_item_title_skips_noname_uses_offer() -> None:
    it = {
        "productName": "noname",
        "offer": {"name": "Корректирующее бельё Nova Classic", "id": 555},
        "quantity": 1,
    }
    assert _item_title(it) == "Корректирующее бельё Nova Classic"


def test_order_source_from_crm_source_dict() -> None:
    o = {"source": {"name": "Сайт", "code": "site"}}
    assert _order_source_display(o) == "Сайт"


def test_order_source_from_order_method_name() -> None:
    o = {"orderMethod": {"name": "Корзина", "code": "cart"}}
    assert _order_source_display(o) == "Корзина"


def test_merged_custom_fields_includes_customer() -> None:
    o = {
        "customFields": {},
        "customer": {"customFields": {"utm_source": "vk"}},
    }
    assert _merged_custom_fields(o).get("utm_source") == "vk"


def test_custom_fields_nested_value_dict() -> None:
    o = {
        "customFields": {
            "utm_source": {"value": "instagram"},
        }
    }
    assert _custom_fields_map(o).get("utm_source") == "instagram"


def test_safe_watermark_blocks_on_unnotified_large_order() -> None:
    last_max = 100
    threshold = Decimal("100000")
    big = {"id": 101, "totalSumm": "500000", "currency": "KZT"}
    small = {"id": 102, "totalSumm": "10", "currency": "KZT"}
    assert (
        _safe_watermark_contiguous(last_max, [big, small], threshold, _DEFAULT_CURRENCIES, set())
        == 100
    )


def test_safe_watermark_advances_through_small_then_big_notified() -> None:
    last_max = 100
    threshold = Decimal("100000")
    big = {"id": 101, "totalSumm": "500000", "currency": "KZT"}
    small = {"id": 102, "totalSumm": "10", "currency": "KZT"}
    assert (
        _safe_watermark_contiguous(
            last_max, [big, small], threshold, _DEFAULT_CURRENCIES, {101}
        )
        == 102
    )


def test_run_once_send_error_does_not_advance_watermark_past_large_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "st.json"
    state.write_text(
        json.dumps({"last_max_order_id": 100, "telegram_notified_ids": []}),
        encoding="utf-8",
    )
    monkeypatch.setattr(tw, "STATE_PATH", state)
    monkeypatch.setenv("TELEGRAM_ORDER_ID_PROBE", "0")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setenv("RETAILCRM_API_URL", "https://example.retailcrm.ru")
    monkeypatch.setenv("RETAILCRM_API_KEY", "key")

    fetched = [
        {"id": 101, "totalSumm": "500000", "currency": "KZT"},
        {"id": 102, "totalSumm": "10", "currency": "KZT"},
    ]

    def _fake_fetch(
        client: object, site: str, last_max: int, max_pages: int | None = None
    ) -> list[dict]:
        assert last_max == 100
        assert site == "s1"
        return list(fetched)

    monkeypatch.setattr(tw, "fetch_orders_newer_than", _fake_fetch)
    monkeypatch.setattr(tw, "read_alert_min_amount_kzt", lambda: "100000")

    mock_client = MagicMock()
    mock_client.resolve_site_code.return_value = "s1"
    mock_client.get_order.return_value = None
    monkeypatch.setattr(tw, "RetailCrmApiClient", MagicMock(return_value=mock_client))

    def _fail_send(**kwargs: object) -> None:
        raise RuntimeError("telegram transport down")

    monkeypatch.setattr(tw, "send_telegram_message", _fail_send)

    assert tw.run_once() == 1
    data = json.loads(state.read_text(encoding="utf-8"))
    assert data["last_max_order_id"] == 100
    assert data.get("telegram_notified_ids", []) == []
