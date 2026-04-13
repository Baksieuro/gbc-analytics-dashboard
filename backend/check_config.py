"""Проверка ролей .env: канон или алиас (секреты не печатаются)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from alert_env import read_alert_min_amount_kzt

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = REPO_ROOT / ".env.example"
DOTENV_PATH = REPO_ROOT / ".env"

REQUIRED_ENV_ROLES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("RETAILCRM_API_URL", ("API_RETAIL_URL_METHODS",)),
    ("RETAILCRM_API_KEY", ("API_RETAIL_TOKEN",)),
    ("SUPABASE_URL", ("NEXT_PUBLIC_SUPABASE_URL", "VITE_SUPABASE_URL")),
    (
        "SUPABASE_ANON_KEY",
        ("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "VITE_SUPABASE_ANON_KEY"),
    ),
    ("VITE_SUPABASE_URL", ("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")),
    (
        "VITE_SUPABASE_ANON_KEY",
        ("SUPABASE_ANON_KEY", "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"),
    ),
    ("TELEGRAM_BOT_TOKEN", ("API_TELEGRAM_TOKEN",)),
    ("TELEGRAM_CHAT_ID", ("TELEGRAM_NAME",)),
)

OPTIONAL_WARN_ROLES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("SUPABASE_SERVICE_ROLE_KEY", ()),
)


def _env_nonempty(name: str) -> bool:
    val = os.environ.get(name)
    return val is not None and str(val).strip() != ""


def _role_satisfied(canonical: str, aliases: tuple[str, ...]) -> bool:
    if _env_nonempty(canonical):
        return True
    return any(alias != canonical and _env_nonempty(alias) for alias in aliases)


def _missing_required_roles() -> list[tuple[str, tuple[str, ...]]]:
    missing: list[tuple[str, tuple[str, ...]]] = []
    for canonical, aliases in REQUIRED_ENV_ROLES:
        if not _role_satisfied(canonical, aliases):
            missing.append((canonical, aliases))
    return missing


def _format_role_hint(canonical: str, aliases: tuple[str, ...]) -> str:
    if not aliases:
        return canonical
    alias_part = ", ".join(aliases)
    return f"{canonical} (или алиас: {alias_part})"


def _service_role_warn_if_needed() -> None:
    canonical, aliases = OPTIONAL_WARN_ROLES[0]
    if _role_satisfied(canonical, aliases):
        return
    hint = _format_role_hint(canonical, aliases)
    print(f"check_config: WARN нет {hint} (нужен для записи в Supabase из Python)", file=sys.stderr)


def main() -> int:
    if not ENV_EXAMPLE.is_file():
        print("check_config: не найден .env.example в корне репозитория", file=sys.stderr)
        return 2

    if not DOTENV_PATH.is_file():
        print("check_config: нет .env (скопируйте из .env.example)", file=sys.stderr)
        return 1

    load_dotenv(DOTENV_PATH, override=False)

    try:
        read_alert_min_amount_kzt()
    except ValueError as e:
        print(f"check_config: {e}", file=sys.stderr)
        return 1

    missing = _missing_required_roles()
    if missing:
        parts: list[str] = []
        for canonical, aliases in missing:
            parts.append(_format_role_hint(canonical, aliases))
        print("check_config: не заданы роли: " + "; ".join(parts), file=sys.stderr)
        return 1

    _service_role_warn_if_needed()

    n = len(REQUIRED_ENV_ROLES)
    print(f"check_config: OK ({n} ролей)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
