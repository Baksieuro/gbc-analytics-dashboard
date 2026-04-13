# GBC Analytics Dashboard

Дашборд заказов: график и сводка по данным из **Supabase**.

## Стек

- **Фронтенд:** React 19, Vite 7, TypeScript (`frontend/`)
- **Данные:** Supabase (Postgres + anon key)

Полный репозиторий (Python backend, тесты, скрипты синхронизации, миграции) — в ветке **`dev`** на GitHub.

## Локальный запуск (из корня репозитория)

```bash
npm install
npm run dev
```

Сборка:

```bash
npm run build
```

Файл `frontend/vite.config.ts` читает переменные `VITE_*` из **корня** репо (удобно держать один `.env` рядом с бэкендом на `dev`).

## Переменные окружения (фронт)

Создайте в корне `.env` (не коммитьте):

| Переменная | Назначение |
|------------|------------|
| `VITE_SUPABASE_URL` | URL проекта Supabase |
| `VITE_SUPABASE_ANON_KEY` | публичный anon key (роль `anon`) |

Другие секреты (RetailCRM, Telegram и т.д.) для этого README не нужны — они используются только в ветке **`dev`** и в Python-скриптах.

## Деплой на Vercel

- **Root Directory:** корень репозитория (там же `package.json` и `vercel.json`).
- Ветка для продакшена: **`main`**.
- В панели Vercel задайте те же `VITE_SUPABASE_*` в **Environment Variables** для Production (и при необходимости Preview).

В репозитории уже есть `vercel.json` (`installCommand`, `buildCommand`, `outputDirectory`: `frontend/dist`).

## Сдача по ТЗ

Итог проверяющей стороне передаётся по условиям задания (ссылка на деплой, репозиторий, ветка **`dev`** для полного кода).
