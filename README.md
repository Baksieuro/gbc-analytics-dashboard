# GBC Analytics Dashboard

Дашборд заказов: график и сводка по данным из **Supabase**.

## Стек

- **Фронтенд:** React 19, Vite 6, TypeScript (`frontend/`)
- **Данные:** Supabase (Postgres + anon key)
- **Интеграции (эта ветка):** Python-скрипты RetailCRM → Supabase, Telegram-уведомления

Ветка **`main`** — минимальное дерево под деплой на Vercel. Ветка **`dev`** (текущая) — полный код: backend, тесты, миграции, вспомогательные материалы.

## Локальный запуск (из корня репозитория)

```bash
npm install
npm run dev
```

Сборка:

```bash
npm run build
```

`frontend/vite.config.ts` читает `VITE_*` из **корня** репозитория (один `.env` для фронта и Python).

## Переменные окружения (фронт)

В корне создайте `.env` (не коммитьте). Шаблон переменных см. в `.env.example`.

| Переменная | Назначение |
|------------|------------|
| `VITE_SUPABASE_URL` | URL проекта Supabase |
| `VITE_SUPABASE_ANON_KEY` | публичный anon key |

Секреты RetailCRM, Telegram и сервисного ключа Supabase для синхронизации описаны в `.env.example` и используются только в Python-скриптах.

## Деплой на Vercel

Продакшен собирается с ветки **`main`**: корень репо, `vercel.json`, переменные `VITE_SUPABASE_*` в настройках проекта Vercel.

## Сдача по ТЗ

Итог проверяющей стороне передаётся по условиям задания (деплой, ссылка на репозиторий; полный код и документы разработки — в **`dev`**).

---

## Разработка

### Python и зависимости

```bash
pip install -r backend/requirements.txt
```

Дополнительно (pytest и прочее из dev-зависимостей):

```bash
pip install -r backend/requirements-dev.txt
```

### Тесты

Из **корня** репозитория:

```bash
pytest
```

Тесты лежат в каталоге `tests/` (`test_alert_env.py`, `test_sync_orders_row.py`, `test_telegram_watch_threshold.py`).

### Тестовые данные

Файл **`mock_orders.json`** — **52** заказа: первые 50 — демо-набор; **51-й** (сумма 40 000 ₸) и **52-й** (60 000 ₸) — для проверки порога `ALERT_MIN_AMOUNT_KZT` (по умолчанию 50 000): уведомление в Telegram должно уйти только на заказ **52** (сумма **строго больше** порога).

Загрузка в RetailCRM из корня репозитория (по умолчанию поднимаются **все** записи из файла):

```bash
python backend/upload_mock_orders.py
```

Дальше синхронизация в Supabase (в `.env` для корректных сумм в ₸ задайте `SYNC_CURRENCY_CODE=KZT`, если CRM отдаёт валюту как RUB):

```bash
python backend/sync_orders_to_supabase.py
```

### Быстрый демо-сценарий Telegram -> CRM -> Supabase -> Dashboard

Одной командой создайте тестовый заказ в RetailCRM и запустите полный пайплайн (синк + Telegram watcher):

```bash
python backend/create_test_order_for_telegram.py --pipeline
```

Ожидаемый результат:
- новый заказ появляется в RetailCRM;
- запись попадает в `public.orders` в Supabase;
- на дашборде Vercel обновляются сумма и количество заказов;
- если сумма > `ALERT_MIN_AMOUNT_KZT`, приходит уведомление в Telegram.

### Каталог `backend/`

Скрипты и модули синхронизации и проверки: например `sync_orders_to_supabase.py`, `telegram_watch_orders.py`, `upload_mock_orders.py`, `check_config.py`, `alert_env.py`, `create_test_order_for_telegram.py`. Зависимости — `backend/requirements.txt` и `backend/requirements-dev.txt`.

### Supabase

SQL-миграции — в **`supabase/migrations/`** (схема таблицы заказов и индексы).
