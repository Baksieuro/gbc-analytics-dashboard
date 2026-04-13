# Отчёт оркестрации orch-20260413-kzt

**Дата:** 2026-04-13  
**Проект:** gbc-analytics-dashboard

## Цель

1. Уведомление в Telegram при **новом** заказе с суммой **строго выше** `ALERT_MIN_AMOUNT_KZT` (по умолчанию 50000), значение из env.  
2. Чистка репозитория: `.gitignore`, краткий README, сокращённые логи/ошибки.

## Выполнено (TASK-1 … TASK-8)

| Задача | Результат |
|--------|-----------|
| TASK-1 | `backend/alert_env.py`, `.env.example`, единое чтение порога |
| TASK-2 | `telegram_watch_orders.py`: строго `>`, state, `telegram_notified_ids`, безопасный watermark при ошибке Telegram |
| TASK-3 | `sync_orders_to_supabase.py`: сумма/валюта согласованы с watcher |
| TASK-4 | `--pipeline` в `create_test_order_for_telegram.py`, общие хелперы в `upload_mock_orders.py` |
| TASK-5 | pytest: env, порог, watcher, sync row |
| TASK-6 | Фронт: валюта из данных, сборка `npm run build` |
| TASK-7 | Расширен `.gitignore`, удалены кэши/dist локально |
| TASK-8 | Краткий README, укорочены сообщения в backend/части frontend |

## Проверка

```powershell
cd <корень-репозитория>
python -m pip install -r requirements-dev.txt
python -m pytest -q
cd frontend
npm ci
npm run build
```

Локальный сценарий алерта (заполненный `.env`):  
`python backend/create_test_order_for_telegram.py --pipeline`

## Ограничения

- При смеси валют в выборке графики/KPI складывают числа; ось ориентируется на доминирующую валюту.  
- В `upload_mock_orders.py` режим `--dry-run` может отличаться от финального тела с `orderType`/`orderMethod`.  
- Субагент documenter не выполнился (регион); отчёт создан вручную оркестратором.
