"""Нормализация строк заказа RetailCRM → Supabase (sync_orders_to_supabase), без сети."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_backend = str(_REPO_ROOT / "backend")
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from sync_orders_to_supabase import (  # noqa: E402
    _crm_currency_code,
    _crm_order_total,
    _sync_currency_override,
    retailcrm_order_to_row,
)


@pytest.mark.parametrize(
    ("order", "expected"),
    [
        ({}, "KZT"),
        ({"currency": ""}, "KZT"),
        ({"currency": "   "}, "KZT"),
        ({"currency": "kzt"}, "KZT"),
        ({"currency": " RUB "}, "RUB"),
        ({"currency": {"code": "usd"}}, "USD"),
        ({"currency": {"currency": "eur"}}, "EUR"),
        ({"currency": {"code": "", "currency": "gbp"}}, "GBP"),
        ({"currency": {"code": None}}, "KZT"),
    ],
)
def test_crm_currency_code(order: dict, expected: str) -> None:
    assert _crm_currency_code(order) == expected


@pytest.mark.parametrize(
    ("order", "expected"),
    [
        ({"totalSumm": "100.5"}, Decimal("100.5")),
        ({"summ": "200"}, Decimal("200")),
        ({"totalSum": "50"}, Decimal("50")),
        ({"totalPrice": "10"}, Decimal("10")),
        ({}, Decimal("0")),
        ({"totalSumm": "", "summ": "7"}, Decimal("7")),
        ({"totalSumm": "  1,25  "}, Decimal("1.25")),
        ({"totalSumm": "not-a-number"}, Decimal("0")),
    ],
)
def test_crm_order_total(order: dict, expected: Decimal) -> None:
    assert _crm_order_total(order) == expected


def test_crm_order_total_prefers_first_non_empty_key() -> None:
    order = {"totalSumm": "1", "summ": "999"}
    assert _crm_order_total(order) == Decimal("1")


def test_retailcrm_order_to_row_happy_path_no_raw() -> None:
    order = {
        "id": 42,
        "totalSumm": "1500.00",
        "currency": {"code": "KZT"},
        "createdAt": "2024-06-01 12:30:45",
    }
    row = retailcrm_order_to_row(order, include_raw=False)
    assert row is not None
    assert row["retailcrm_id"] == 42
    assert row["total_amount"] == 1500.0
    assert row["currency"] == "KZT"
    assert row["ordered_at"] == "2024-06-01T12:30:45+00:00"
    assert "raw_payload" not in row


def test_retailcrm_order_to_row_sync_currency_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SYNC_CURRENCY_CODE", "KZT")
    try:
        assert _sync_currency_override() == "KZT"
        order = {
            "id": 1,
            "summ": "100",
            "currency": {"code": "RUB"},
            "createdAt": "2024-01-01T00:00:00+00:00",
        }
        row = retailcrm_order_to_row(order, include_raw=False)
        assert row is not None
        assert row["currency"] == "KZT"
    finally:
        monkeypatch.delenv("SYNC_CURRENCY_CODE", raising=False)


def test_retailcrm_order_to_row_string_id_and_include_raw() -> None:
    order = {
        "id": "99",
        "summ": "10",
        "currency": "rub",
        "createdAt": "2024-01-15T10:00:00Z",
    }
    row = retailcrm_order_to_row(order, include_raw=True)
    assert row is not None
    assert row["retailcrm_id"] == 99
    assert row["total_amount"] == 10.0
    assert row["currency"] == "RUB"
    assert row["ordered_at"] == "2024-01-15T10:00:00+00:00"
    assert row["raw_payload"] == order


def test_retailcrm_order_to_row_currency_truncated_to_16() -> None:
    long_code = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    order = {
        "id": 1,
        "totalSumm": "0",
        "currency": long_code,
        "createdAt": "2024-01-01T00:00:00+00:00",
    }
    row = retailcrm_order_to_row(order, include_raw=False)
    assert row is not None
    assert row["currency"] == long_code[:16]


@pytest.mark.parametrize("bad_id", (None, "x", [], {}))
def test_retailcrm_order_to_row_returns_none_on_invalid_id(bad_id: object) -> None:
    order = {
        "id": bad_id,
        "totalSumm": "100",
        "currency": "KZT",
        "createdAt": "2024-01-01T00:00:00+00:00",
    }
    assert retailcrm_order_to_row(order, include_raw=False) is None


def test_retailcrm_order_to_row_raw_payload_for_non_dict_mapping() -> None:
    inner = {
        "id": 5,
        "totalSumm": "1",
        "currency": "KZT",
        "createdAt": "2024-02-02T08:00:00+00:00",
    }
    order = MappingProxyType(inner)
    row = retailcrm_order_to_row(order, include_raw=True)
    assert row is not None
    assert row["retailcrm_id"] == 5
    assert row["raw_payload"] == {"value": order}


def test_retailcrm_order_to_row_ordered_at_fallback_keys() -> None:
    base = {"id": 7, "totalSumm": "0", "currency": "KZT"}
    assert "createdAt" not in base
    row_date = retailcrm_order_to_row(
        {**base, "orderDate": "2023-12-31 23:59:59"},
        include_raw=False,
    )
    assert row_date is not None
    assert row_date["ordered_at"] == "2023-12-31T23:59:59+00:00"

    row_status = retailcrm_order_to_row(
        {**base, "statusUpdatedAt": "2023-11-11T11:11:11Z"},
        include_raw=False,
    )
    assert row_status is not None
    assert row_status["ordered_at"] == "2023-11-11T11:11:11+00:00"
