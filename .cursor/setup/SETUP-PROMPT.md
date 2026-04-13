# Промпт для генерации Cursor Setup (оркестратор + субагенты)

Скопируйте **весь документ** (или блок «Инструкция для LLM» ниже) в чат Cursor/другой среды с агентом и выполните шаги. Цель — получить структуру папки `.cursor/`, эквивалентную эталонной (~37 файлов без учёта этого файла; с ним — +1), с теми же ролями: **rules**, **skills**, **субагенты (agents)**, **команды (commands)**, **config**, **hooks**, **setup/README.md** и сопутствующая документация в `setup/`.

---

## Краткий разбор эталонной установки (смысл и фокус)

**Назначение:** универсальная среда для разработки в Cursor с **оркестрацией через субагентов** (инструмент `Task` / аналог). Главный агент в чате — **только координатор**: не пишет код, не правит файлы проекта и не гоняет тесты сам; каждый этап делегируется специализированному субагенту.

**Фокус разработки (как заложено в правилах и skills):**

- **Качество и сопровождаемость:** стандарты кода, ревью, рефакторинг, архитектурные принципы (SOLID, паттерны, границы модулей).
- **Безопасность:** критические запреты в rules + отдельный skill и агент security-auditor для задач с API, auth, данными.
- **Тестирование:** пирамида тестов, AAA; в workflows обязательны написание тестов (test-writer) и верификация (test-runner), если не отключено конфигом.
- **Документация:** отдельное дерево `ai_docs/` (или настраиваемые пути в `config.json`) — планы, отчёты, ADR, API, компоненты, аудиты и т.д.; documenter пишет туда по конфигу.
- **Git-дисциплина:** ветки, Conventional Commits, описание PR — в rules.
- **Оркестрация:** временное состояние в `.cursor/workspace/` (active/completed/failed), постоянная документация — по путям из `config.json`; planner ведёт план и задачи.

**Стек в материалах:** правила и агенты ориентированы на **полиглотность** (в первую очередь JS/TS, Python, Go в подсказках автоопределения); конкретный стек проекта вы задаёте в конфигурации ниже — агенты test-writer/test-runner должны быть сформулированы под него.

**Команды пользователя:** слэш-команды `/implement`, `/orchestrate`, `/refactor`, `/review`, `/audit` — каждая только читает соответствующий skill и вызывает цепочку субагентов.

---

## Блок конфигурации будущей установки (заполните перед запуском промпта)

Скопируйте и заполните. LLM обязан **учесть все поля** при генерации текстов агентов/skills и разделов README.

```yaml
# === CURSOR SETUP — параметры генерации ===

project_name: "Название проекта или репозитория"

# Тестовый контур (субагенты test-writer / test-runner)
# - full: worker → test-writer → test-runner (как в эталоне implement/orchestrate)
# - verify_only: worker → test-runner (тесты пишет сам worker или уже есть)
# - off: без test-writer и без test-runner в цепочках (только явные ручные вызовы при необходимости)
testing_pipeline: full   # full | verify_only | off

# Предполагаемый стек (свободный текст — попадёт в README и в «Project-Specific» ориентиры агентов)
backend_stack: "например: Python 3.13, FastAPI, PostgreSQL, SQLAlchemy 2"
frontend_stack: "например: React 19, TypeScript, Vite"

# Фокус разработки (один вариант) — усиливает формулировки в rules/README/agents под сценарий
# - backend_focused
# - frontend_focused
# - website_creation        # лендинги, маркетинговые сайты, SSR/SSG
# - application_development # полноценные приложения (web/mobile/desktop) end-to-end
# - bot_development         # чат-боты, Telegram/Discord, интеграции с мессенджерами
development_focus: application_development

# Документация (как в эталонном config.json или свои пути)
documentation_root: "ai_docs"   # корень; остальные подпути можно оставить как в эталоне

# Опционально: включить примеры хуков (по умолчанию hooks.json пустой, как в эталоне)
hooks_examples_in_hooks_md: true   # true | false
```

---

## Инструкция для LLM (выполняй по шагам)

Ты — агент в репозитории пользователя. Нужно **создать или пересобрать** каталог `.cursor/` по спецификации. Не выходи за рамки задачи: не добавляй лишних агентов и команд без запроса.

### Шаг 0 — Входные данные

1. Прочитай YAML-блок «CURSOR SETUP — параметры генерации» из сообщения пользователя (если чего-то нет — используй значения по умолчанию из примера выше и явно перечисли допущения в конце).
2. Учти `development_focus` и стеки при формулировке примеров в README и при приоритизации упоминаний в rules (например, для `bot_development` чаще упоминай webhook’и, идемпотентность, rate limits; для `website_creation` — доступность, SEO, производительность фронта).

### Шаг 1 — Дерево каталогов

Создай структуру:

```text
.cursor/
├── agents/           # ровно 10 файлов .md — см. шаг 4
├── commands/         # ровно 5 файлов .md — см. шаг 5
├── skills/           # 11 подкаталогов, в каждом SKILL.md — см. шаг 3
├── rules/            # ровно 5 файлов .md — см. шаг 2
├── setup/
│   ├── README.md     # подробный, см. шаг 6
│   ├── HOOKS.md
│   ├── configure-agents.md
│   └── SETUP-PROMPT.md   # опционально: скопируй этот шаблон как есть для повторного тиражирования
├── workspace/
│   └── .gitignore
├── config.json
└── hooks.json
```

Итого **37 файлов** в эталоне без `SETUP-PROMPT.md`; после добавления `SETUP-PROMPT.md` в `setup/` получится **38**.

### Шаг 2 — Rules (`.cursor/rules/`)

Создай файлы с YAML frontmatter (`description`, при необходимости `globs`):

| Файл | Назначение |
|------|------------|
| `testing.md` | Пирамида тестов, AAA, что тестировать, именование; `globs` под тестовые файлы. |
| `security.md` | NEVER/ALWAYS, OWASP-ориентир, ссылка на skill security-guidelines для auth/API/PII. |
| `documentation.md` | Когда документировать (JSDoc и аналоги), формат; `globs` под исходники. |
| `commit-messages.md` | Conventional Commits, типы коммитов, примеры. |
| `git-workflow.md` | Именование веток, PR, мелкие best practices; `globs: []`. |

Согласуй примеры с `development_focus` и стеками (не переписывай всё под один язык — сохрани универсальность, но акценты добавь).

**Важно:** файла `coding-standards.md` в эталоне **нет**; стандарты кода живут в skill `code-quality-standards` и в агенте worker.

### Шаг 3 — Skills (`.cursor/skills/<name>/SKILL.md`)

У каждого skill — frontmatter с `name` и `description`. Содержимое: чёткие фазы, для оркестрации — псевдокод чтения `config.json` и путей workspace, лимиты ретраев (например debugger до 3 раз), запрет координатору делать работу самому.

| Каталог skill | Назначение |
|---------------|------------|
| `simple-workflow` | Цепочка для `/implement`: worker → (опционально test-writer) → (опционально test-runner) → documenter. **Зависит от `testing_pipeline`.** |
| `orchestration` | Полный цикл `/orchestrate`: planner → для каждой задачи worker → test-writer? → test-runner? → debugger↔test-runner → reviewer↔debugger → следующая задача → documenter. **Укороти цепочку согласно `testing_pipeline`.** |
| `refactor-workflow` | `/refactor`: senior-reviewer → refactor → test-runner? → debugger? → documenter. |
| `review-workflow` | `/review`: reviewer → (опционально debugger) → test-runner?. |
| `audit-workflow` | `/audit`: senior-reviewer → security-auditor → reviewer → documenter → опциональное исправление по согласию. |
| `task-management` | Имена/форматы task id, обновление plan/progress/tasks.json, ссылки на документацию. |
| `docs` | Структура `documentation.paths` из config, куда писать планы/отчёты/ADR. |
| `git-helper` | Ветки, коммиты, squash/rebase осторожно — в духе rules. |
| `security-guidelines` | Углублённо для worker/security-auditor. |
| `architecture-principles` | SOLID, границы, зависимости — для worker/senior-reviewer. |
| `code-quality-standards` | Читаемость, сложность, дублирование — для worker/reviewer/debugger. |

Если `testing_pipeline: off`, в skills **явно** опиши: пропуск шагов test-writer и test-runner и предупреждение в README, что верификация ложится на пользователя или ручной вызов `/test-runner`.

Если `verify_only`, убери вызовы test-writer из цепочек, оставь test-runner после worker.

### Шаг 4 — Agents (`.cursor/agents/*.md`)

Для **каждого** файла: frontmatter с полями как минимум `name`, `description`, `model: inherit`, `readonly`, `is_background` (как в эталоне). Поле `name` должно совпадать с типом субагента, который вызывает координатор (kebab-case: `test-runner`, `test-writer`, `security-auditor`, `senior-reviewer`).

Список **10 агентов** (имена файлов = `<name>.md`):

1. **worker** — только реализация; в начале читает `code-quality-standards`; условно security + architecture skills.
2. **planner** — разбиение на задачи, workspace, plan, progress, tasks, links.
3. **test-writer** — пишет тесты, не запускает; секция «Project-Specific Instructions» + автоопределение стека; **если testing_pipeline без full — файл оставить, но в skills не вызывать**, либо краткая пометка в агенте «используется только при full».
4. **test-runner** — линт, typecheck, тесты, верификация; секция «Project-Specific Commands»; для `off` — не вызывать из workflows.
5. **debugger** — починка по логам ревью/тестов.
6. **reviewer** — код-ревью.
7. **refactor** — рефакторинг без смены поведения.
8. **security-auditor** — аудит безопасности.
9. **senior-reviewer** — архитектура, крупные решения.
10. **documenter** — документация в пути из config; обновление changelog/отчётов по шаблонам skill docs.

В теле агентов встрой **контекст стека** из YAML (короткий абзац «типичный стек проекта»), не дублируя целые туториалы.

### Шаг 5 — Commands (`.cursor/commands/*.md`)

Пять файлов с frontmatter `name`, `description`. Тело команды **одинаковой структуры**:

- Запрет координатору делать работу самому (код/тесты/ревью).
- Обязательный пункт: прочитать соответствующий skill через Read tool и выполнить **только** через вызовы субагентов (`Task` или эквивалент в среде).

| Файл | `name` | Читает skill |
|------|--------|----------------|
| `implement.md` | implement | `.cursor/skills/simple-workflow/SKILL.md` |
| `orchestrate.md` | orchestrate | `.cursor/skills/orchestration/SKILL.md` |
| `refactor.md` | refactor | `.cursor/skills/refactor-workflow/SKILL.md` |
| `review.md` | review | `.cursor/skills/review-workflow/SKILL.md` |
| `audit.md` | audit | `.cursor/skills/audit-workflow/SKILL.md` |

В Cursor пользователь вызывает: **`/implement`**, **`/orchestrate`**, **`/refactor`**, **`/review`**, **`/audit`**.

Субагенты вызываются по именам: **`worker`**, **`planner`**, **`test-writer`**, **`test-runner`**, **`debugger`**, **`reviewer`**, **`refactor`**, **`security-auditor`**, **`senior-reviewer`**, **`documenter`** (в т.ч. вручную в чате, если поддерживается).

### Шаг 6 — `config.json`

Воссоздай схему:

- `workspace.path` — например `.cursor/workspace`.
- `workspace.cleanup` — `autoCleanCompleted`, `cleanupAfterDays`, `keepFailed` (как минимум совместимо с эталоном).
- `documentation.paths` — `root` = `documentation_root` из YAML пользователя; остальные ключи: `plans`, `reports`, `issues`, `architecture`, `features`, `api`, `components`, `design`, `changelog`, `audits`.
- `documentation.enabled` — булевы флаги по типам документов.

Добавь комментарий-ключ `"comment"` с подсказкой по кастомизации (как в эталоне).

### Шаг 7 — `hooks.json`

Эталон: `version: 1`, пустые массивы `afterFileEdit`, `subagentStop`. Не добавляй хуки, если пользователь не просил.

### Шаг 8 — `workspace/.gitignore`

Игнорируй `active/`, `completed/`, `failed/`; разреши `.gitignore` и при необходимости `README.md` (как в эталоне).

### Шаг 9 — `setup/README.md` (обязательно подробный)

Должен включать разделы (можно на русском, как в эталоне):

1. Заголовок и краткое описание (оркестрация в одном чате).
2. Быстрый старт: примеры `/implement` и `/orchestrate`.
3. Таблица команд и сравнение workflows.
4. Настройка: `config.json`, предупреждение про скрытую папку `.cursor`, `.gitignore` для `workspace/`.
5. Ссылка на `configure-agents.md` для test-runner и test-writer.
6. Дерево структуры `.cursor/` с **актуальным** списком rules (5 файлов), skills (11), agents (10), commands (5).
7. Пошаговое описание каждого workflow (implement, orchestrate, refactor, review, audit) — диаграммы mermaid по желанию.
8. Таблица агентов: имя, слэш, роль, в каких командах используется; **включи test-writer** и не путай команду `/refactor` с агентом `refactor`.
9. Примеры ручного комбинирования агентов.
10. Workspace vs постоянная документация.
11. FAQ.
12. Инструкция «копирование в новый проект».
13. Философия (skills, конфигурируемость, видимость шагов).
14. Упоминание `HOOKS.md` и опциональных хуков.

Впиши **project_name**, стеки и `development_focus` из YAML в вводный абзац или секцию «Настройка под проект».

### Шаг 10 — `setup/HOOKS.md` и `setup/configure-agents.md`

- **HOOKS.md:** типы хуков, переменные окружения, готовые «промпты для AI» (форматирование, lint-fix, тесты после субагента, кастомный хук), советы non-blocking. Если `hooks_examples_in_hooks_md: false`, всё равно опиши концепцию, но сократи примеры.
- **configure-agents.md:** два больших промпта — сканирование проекта и настройка `test-writer.md` (ветка «тесты есть / тестов нет») и `test-runner.md` (команды lint/typecheck/test из репозитория).

### Шаг 11 — Самопроверка

Выведи пользователю:

- Число созданных файлов и список путей.
- Какие шаги изменены из-за `testing_pipeline`.
- Напоминание добавить в корневой `.gitignore`: `.cursor/workspace/`.
- Если что-то в YAML было не заполнено — перечисли принятые по умолчанию значения.

---

## Сводка: команды и субагенты (шпаргалка для пользователя)

| Команда | Назначение |
|---------|------------|
| `/implement` | Простая задача: код → тесты (если включено) → проверка (если включена) → документация. |
| `/orchestrate` | План → цикл задач с ревью и отладкой → документация. |
| `/refactor` | Анализ (senior-reviewer) → рефакторинг → проверка → документация. |
| `/review` | Ревью → опционально фиксы → проверка. |
| `/audit` | Архитектура → безопасность → качество → отчёт. |

| Субагент | Роль |
|----------|------|
| worker | Код |
| planner | План и задачи |
| test-writer | Написание тестов |
| test-runner | Линт, тесты, верификация |
| debugger | Исправления по сбоям/ревью |
| reviewer | Код-ревью |
| refactor | Рефакторинг |
| security-auditor | Безопасность |
| senior-reviewer | Архитектура |
| documenter | Документация |

---

## Примечание для оператора

Этот файл — **генератор установки**. Эталонная копия skills/agents содержит длинные тексты; при генерации «с нуля» LLM должен **воспроизвести поведение и структуру**, а не обязательно побайтно совпасть с оригиналом. Если нужна идентичная копия — проще скопировать готовую папку `.cursor/` из репозитория-образца; этот промпт — для **воссоздания с нуля с параметризацией** под новый проект и машину.
