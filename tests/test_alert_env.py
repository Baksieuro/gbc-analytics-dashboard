"""Тесты порога ALERT_MIN_AMOUNT_KZT (backend/alert_env.py)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_backend = str(_REPO_ROOT / "backend")
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from alert_env import (  # noqa: E402
    ALERT_MIN_AMOUNT_KZT_VAR,
    DEFAULT_ALERT_MIN_AMOUNT_KZT,
    read_alert_min_amount_kzt,
)


@pytest.fixture
def no_alert_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ALERT_MIN_AMOUNT_KZT_VAR, raising=False)


def test_default_when_env_var_absent(no_alert_env_var: None) -> None:
    assert read_alert_min_amount_kzt() == DEFAULT_ALERT_MIN_AMOUNT_KZT


@pytest.mark.parametrize("raw", ("", "   ", "\t\n"))
def test_default_when_env_var_blank(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv(ALERT_MIN_AMOUNT_KZT_VAR, raw)
    assert read_alert_min_amount_kzt() == DEFAULT_ALERT_MIN_AMOUNT_KZT


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0", 0),
        ("1", 1),
        ("50000", 50000),
        ("750000", 750000),
        ("  123  ", 123),
    ],
)
def test_valid_integer_parsing(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: int
) -> None:
    monkeypatch.setenv(ALERT_MIN_AMOUNT_KZT_VAR, raw)
    assert read_alert_min_amount_kzt() == expected


@pytest.mark.parametrize("raw", ("abc", "12.5", "1e6", "0x10"))
def test_invalid_string_raises_value_error(
    monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    monkeypatch.setenv(ALERT_MIN_AMOUNT_KZT_VAR, raw)
    with pytest.raises(ValueError, match="ожидается целое число"):
        read_alert_min_amount_kzt()


@pytest.mark.parametrize("raw", ("-1", "-999"))
def test_negative_raises_value_error(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv(ALERT_MIN_AMOUNT_KZT_VAR, raw)
    with pytest.raises(ValueError, match="ожидается >= 0"):
        read_alert_min_amount_kzt()
