"""Чтение порога суммы для алертов из окружения (backend)."""

from __future__ import annotations

import os

ALERT_MIN_AMOUNT_KZT_VAR = "ALERT_MIN_AMOUNT_KZT"
DEFAULT_ALERT_MIN_AMOUNT_KZT = 50000


def read_alert_min_amount_kzt() -> int:
    raw = os.environ.get(ALERT_MIN_AMOUNT_KZT_VAR)
    if raw is None or str(raw).strip() == "":
        return DEFAULT_ALERT_MIN_AMOUNT_KZT
    s = str(raw).strip()
    try:
        n = int(s, 10)
    except ValueError as e:
        raise ValueError(f"{ALERT_MIN_AMOUNT_KZT_VAR}: ожидается целое число, не {raw!r}") from e
    if n < 0:
        raise ValueError(f"{ALERT_MIN_AMOUNT_KZT_VAR}: ожидается >= 0, не {n}")
    return n
