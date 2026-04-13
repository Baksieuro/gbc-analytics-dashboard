---
name: task-management
description: Учёт задач и планов. Planner создаёт планы и задачи, оркестратор читает/обновляет прогресс, documenter — отчёты о завершении, любой агент — некритичные issues.
---

# Skill: управление задачами

**Назначение:** планы, задачи, отчёты и issues через гибрид **временного workspace** и **постоянной документации**.

---

## Архитектура

### Два уровня

**1. Workspace (временный) — `.cursor/workspace/`**
- метаданные и состояние оркестрации
- статусы задач и прогресс
- очистка после завершения

**2. Документация (постоянная) — пути из config**
- планы, отчёты, архитектурные решения
- итоговая документация по фичам
- хранится в выбранной структуре проекта

---

## Конфигурация

**Читать из:** `.cursor/config.json`

```json
{
  "workspace": {
    "path": ".cursor/workspace",
    "cleanup": {
      "autoCleanCompleted": true,
      "cleanupAfterDays": 7
    }
  },
  "documentation": {
    "paths": {
      "root": "docs",
      "reports": "docs/reports",
      "issues": "docs/issues",
      "architecture": "docs/architecture",
      "plans": "docs/plans"
    }
  }
}
```

**Примечание:** все пути настраиваются; в примере `docs/`, у вас может быть `ai_docs/` и т.д.

**Значения по умолчанию, если config нет:**
- workspace: `.cursor/workspace`
- root: `ai_docs`
- reports: `ai_docs/develop/reports`
- issues: `ai_docs/develop/issues`
- architecture: `ai_docs/develop/architecture`
- plans: `ai_docs/develop/plans`

---

## Структура каталогов

### Workspace (временный)

```
.cursor/workspace/
├── active/                          # Текущие оркестрации
│   └── orch-2026-02-10-15-30-auth/
│       ├── progress.json            # Статус, время, счётчики
│       ├── tasks.json               # Статусы задач
│       └── links.json               # Ссылки на файлы доков
├── completed/                       # Автоочистка через N дней
└── failed/                          # Можно продолжить
```

### Документация (постоянная)

```
{configured-path}/                   # Из config.json
├── plans/                           # Планы верхнего уровня
│   └── 2026-02-10-auth-system.md
├── reports/                         # Отчёты о завершении
│   └── 2026-02-10-auth-implementation.md
└── issues/                          # Известные проблемы
    └── ISS-001-token-race.md
```

---

## Форматы файлов

### Файлы workspace (временные)

#### progress.json
```json
{
  "id": "orch-2026-02-10-15-30-auth",
  "name": "Authentication System",
  "status": "in-progress",
  "started": "2026-02-10T15:30:00Z",
  "lastUpdated": "2026-02-10T15:45:00Z",
  "tasksTotal": 5,
  "tasksCompleted": 2,
  "currentTask": "AUTH-003"
}
```

#### tasks.json
```json
{
  "AUTH-001": {
    "id": "AUTH-001",
    "name": "User Model",
    "status": "completed",
    "startedAt": "2026-02-10T15:30:00Z",
    "completedAt": "2026-02-10T15:40:00Z",
    "filesChanged": ["src/models/User.ts"],
    "testsRun": 5,
    "testsPassed": 5
  },
  "AUTH-002": {
    "id": "AUTH-002",
    "status": "in-progress",
    "startedAt": "2026-02-10T15:40:00Z"
  }
}
```

#### links.json
```json
{
  "plan": "{configured-path}/plans/2026-02-10-auth-system.md",
  "report": null
}
```

**Note:** Path is from `.cursor/config.json` → `documentation.paths.plans`

---

### Файлы документации (постоянные)

#### plans/ — планы
**Создаёт:** Planner  
**Место:** workspace (временно) или файл пользователя

**Формат:**
```markdown
# План: Система аутентификации

**Создан:** 2026-02-10
**Оркестрация:** orch-2026-02-10-15-30-auth
**Статус:** 🔄 В работе

## Цель
Внедрить JWT-аутентификацию с управлением пользователями.

## Задачи
- [ ] AUTH-001: Модель пользователя (⏳ ожидает)
- [ ] AUTH-002: Утилиты JWT (⏳ ожидает)
- [ ] AUTH-003: Middleware авторизации (⏳ ожидает)
- [ ] AUTH-004: API-эндпоинты (⏳ ожидает)
- [ ] AUTH-005: Тестирование (⏳ ожидает)

## Зависимости
- AUTH-002 после AUTH-001
- AUTH-003 после AUTH-002

## Архитектурные решения
- JWT с refresh-токенами
- Хеширование паролей bcrypt
```

#### reports/ — отчёты о завершении
**Создаёт:** Documenter  
**Путь:** `{config.documentation.paths.reports}/`

**Формат:**
```markdown
# Отчёт: внедрение системы аутентификации

**Дата:** 2026-02-10
**Оркестрация:** orch-2026-02-10-15-30-auth
**Статус:** ✅ Завершено

## Краткое резюме
Реализована полная JWT-аутентификация с управлением пользователями.

## Что сделано
- Модель пользователя с хешированием паролей
- Генерация и проверка JWT
- Middleware для защищённых маршрутов
- Эндпоинты логина и регистрации
- Покрытие тестами

## Выполненные задачи
1. ✅ AUTH-001: Модель пользователя (25 мин)
2. ✅ AUTH-002: Утилиты JWT (30 мин)
3. ✅ AUTH-003: Middleware авторизации (20 мин)
4. ✅ AUTH-004: API-эндпоинты (35 мин)
5. ✅ AUTH-005: Тестирование (40 мин)

## Метрики
- создано 8 файлов
- 320 строк кода
- 15 тестов (все проходят)
- 0 ошибок линтера

## Известные проблемы
- ISS-001: гонка при refresh токена (низкий приоритет)
```

#### issues/ — известные проблемы
**Создаёт:** любой агент  
**Путь:** `{config.documentation.paths.issues}/`

**Формат:**
```markdown
# Issue: гонка при обновлении токена

**ID:** ISS-001
**Создан:** 2026-02-10
**Серьёзность:** низкая
**Статус:** Открыт

## Описание
Возможная гонка при одновременном refresh токенов.

## Влияние
- редко проявляется
- безопасность не затронута
- незначительный UX

## Почему не сейчас
- низкий приоритет
- нужен Redis для распределённой блокировки
- для MVP текущей реализации достаточно

## Предлагаемое решение
Распределённая блокировка через Redis при масштабировании.

## Связь
- Оркестрация: orch-2026-02-10-15-30-auth
- Задача: AUTH-002
```

---

## Сценарии (workflows)

### Вспомогательно: чтение конфига

**Сначала всегда читай config:**

```javascript
config = readJSON(".cursor/config.json")
if (!config) {
  // Значения по умолчанию
  config = {
    workspace: { path: ".cursor/workspace" },
    documentation: {
      paths: {
        root: "ai_docs",
        plans: "ai_docs/develop/plans",
        reports: "ai_docs/develop/reports",
        issues: "ai_docs/develop/issues",
        architecture: "ai_docs/develop/architecture",
        features: "ai_docs/develop/features",
        api: "ai_docs/develop/api",
        components: "ai_docs/develop/components",
        design: "ai_docs/design",
        changelog: "ai_docs/changelog"
      }
    }
  }
}

workspacePath = config.workspace.path
docsReports = config.documentation.paths.reports  // null = disabled
docsIssues = config.documentation.paths.issues    // null = disabled
docsArchitecture = config.documentation.paths.architecture  // null = disabled
```

**Перед записью:**

```javascript
// Пример: отчёт только если включено
if (docsReports !== null) {
  reportFile = `${docsReports}/2026-02-10-auth-report.md`
  write(reportFile, reportContent)
} else {
  // Отчёты отключены — только в чат
  return "Report: [content in chat only]"
}

// Пример: issue только если включено
if (docsIssues !== null) {
  issueFile = `${docsIssues}/ISS-001-token-race.md`
  write(issueFile, issueContent)
} else {
  // Только предупреждение в чат
  warn("⚠️ Issue found: token race condition (low priority)")
}
```

---

## Workflow planner

### Шаг 0: тип ввода

```javascript
// Файл задач от пользователя
userInput = getUserInput()
taskFile = detectTaskFile(userInput) // e.g., @TODO.md, @roadmap.md

if (taskFile) {
  // Режим: обновление файла
  mode = "file"
  planFile = taskFile
} else {
  // Режим: временный план
  mode = "temporary"
  planFile = null
}
```

### Шаг 1: инициализация оркестрации

```javascript
// ID оркестрации
timestamp = formatDate(now(), "YYYY-MM-DD-HH-mm")
slug = slugify(taskName) // "auth-system" → "auth"
orchestrationId = `orch-${timestamp}-${slug}`

// Создать workspace
workspaceDir = `${config.workspace.path}/active/${orchestrationId}`
createDirectory(workspaceDir)

// progress.json
write(`${workspaceDir}/progress.json`, {
  id: orchestrationId,
  name: taskName,
  status: "planning",
  started: now(),
  tasksTotal: 0,
  tasksCompleted: 0,
  mode: mode,  // "file" or "temporary"
  sourceFile: taskFile || null
})
```

### Шаг 2: план

**Режим A: временный план (файла нет)**

```javascript
// Содержимое плана
planContent = generatePlan(taskDescription)

// Ссылки в workspace (план только в workspace)
write(`${workspaceDir}/links.json`, {
  plan: null,
  report: null,
  temporary: true
})

// plan.md в workspace
write(`${workspaceDir}/plan.md`, planContent)

// Initialize tasks tracking
write(`${workspaceDir}/tasks.json`, {})
```

**Режим B: файл задач пользователя**

```javascript
// Чтение файла задач
taskFile = progress.sourceFile  // e.g., "TODO.md"
existingContent = read(taskFile)

// Разбор задач
tasks = parseTasks(existingContent)

// Save link in workspace
write(`${workspaceDir}/links.json`, {
  plan: taskFile,
  report: null,
  temporary: false
})

// tasks.json из файла
write(`${workspaceDir}/tasks.json`, tasks)
```

**Общее: обновить progress**

```javascript
updateJSON(`${workspaceDir}/progress.json`, {
  status: "ready",
  tasksTotal: taskCount
})
```

### Шаг 3: ответ пользователю

```markdown
✅ Plan created: {planFile}
🎯 Tasks: {taskCount} tasks ({taskIds})
📂 Orchestration: {orchestrationId}

Запуск: /orchestrate execute {orchestrationId}
```

---

## Workflow оркестратора

### Шаг 1: загрузка оркестрации

```javascript
// Поиск оркестрации
orchestrationId = userInput || findLatestActive()
workspaceDir = `${config.workspace.path}/active/${orchestrationId}`

// Метаданные
progress = readJSON(`${workspaceDir}/progress.json`)
links = readJSON(`${workspaceDir}/links.json`)
tasksState = readJSON(`${workspaceDir}/tasks.json`)

// План
planContent = read(links.plan)
taskIds = extractTaskIds(planContent)
```

### Шаг 2: цикл задач

```javascript
for (taskId of taskIds) {
  // Уже выполнено — пропуск
  if (tasksState[taskId]?.status === "completed") continue
  
  // Статус in-progress
  tasksState[taskId] = {
    id: taskId,
    status: "in-progress",
    startedAt: now()
  }
  write(`${workspaceDir}/tasks.json`, tasksState)
  
  // Update plan/task file
  if (links.plan) {
    // Mode B: Update user's task file
    updateTaskInFile(links.plan, taskId, "🔄 In Progress")
  } else {
    // Mode A: Update workspace plan
    updateTaskInFile(`${workspaceDir}/plan.md`, taskId, "🔄 In Progress")
  }
  
  // Выполнение задачи
  result = callWorker(taskId, taskDetails)

  // Тесты к реализации
  testWriterResult = callTestWriter(result.filesChanged)

  // Тесты и верификация
  testAndVerifyPassed = callTestRunner()
  reviewPassed = callReview()
  
  // Задача completed
  tasksState[taskId] = {
    ...tasksState[taskId],
    status: "completed",
    completedAt: now(),
    filesChanged: result.filesChanged,
    testsRun: testsPassed.total,
    testsPassed: testsPassed.passed
  }
  write(`${workspaceDir}/tasks.json`, tasksState)
  
  // Update plan/task file
  if (links.plan) {
    // Mode B: Update user's task file
    updateTaskInFile(links.plan, taskId, "✅ Completed")
  } else {
    // Mode A: Update workspace plan
    updateTaskInFile(`${workspaceDir}/plan.md`, taskId, "✅ Completed")
  }
  
  // progress
  updateJSON(`${workspaceDir}/progress.json`, {
    tasksCompleted: progress.tasksCompleted + 1,
    lastUpdated: now()
  })
}
```

### Шаг 3: финализация

```javascript
// Статус
updateJSON(`${workspaceDir}/progress.json`, {
  status: "documenting"
})

// Documenter — отчёт
reportFile = callDocumenter(orchestrationId, links.plan, tasksState)

// Ссылка на отчёт
updateJSON(`${workspaceDir}/links.json`, {
  report: reportFile
})

// completed
updateJSON(`${workspaceDir}/progress.json`, {
  status: "completed",
  completedAt: now(),
  reportFile: reportFile
})

// active → completed
move(
  `${config.workspace.path}/active/${orchestrationId}`,
  `${config.workspace.path}/completed/${orchestrationId}`
)
```

---

## Workflow documenter

### Отчёт о завершении

```javascript
// Метаданные оркестрации
workspaceDir = `${config.workspace.path}/completed/${orchestrationId}`
progress = readJSON(`${workspaceDir}/progress.json`)
links = readJSON(`${workspaceDir}/links.json`)
tasksState = readJSON(`${workspaceDir}/tasks.json`)

// План
planContent = read(links.plan)

// Текст отчёта
reportContent = generateReport({
  orchestrationId: progress.id,
  name: progress.name,
  started: progress.started,
  completed: progress.completedAt,
  tasks: tasksState,
  planFile: links.plan
})

// Запись в документацию
reportFile = `${docsReports}/${formatDate(now(), "YYYY-MM-DD")}-${slug}-implementation.md`
write(reportFile, reportContent)

// links.json
updateJSON(`${workspaceDir}/links.json`, {
  report: reportFile
})
```

---

## Любой агент: создание issues

### Когда создавать issue

**Создавай issue, когда:**
- ✅ Non-critical problem found
- ✅ Enhancement idea
- ✅ Tech debt identified
- ✅ Don't want to block current work

**Не создавай issue, когда:**
- ❌ Critical bug (fix immediately via debugger)
- ❌ Blocks current task
- ❌ Simple fix (< 5 min)

### Создание issue

```javascript
// config
config = readJSON(".cursor/config.json")
issuesPath = config.documentation.paths.issues || "ai_docs/develop/issues"

// ID issue
lastIssueId = findLastIssueId(issuesPath) // ISS-003
nextIssueId = incrementId(lastIssueId) // ISS-004

// Файл issue
issueFile = `${issuesPath}/ISS-${nextIssueId}-${slug}.md`
write(issueFile, issueContent)

// Опционально: ссылка на оркестрацию
if (currentOrchestration) {
  // Ссылка в тексте issue
  addReference(issueFile, {
    orchestration: currentOrchestration.id,
    task: currentTask.id
  })
}
```

---

## Соглашения об именах

### ID оркестраций
```
Format: orch-YYYY-MM-DD-HH-mm-{slug}

Examples:
- orch-2026-02-10-15-30-auth
- orch-2026-02-10-16-45-payments
- orch-2026-02-11-09-00-refactor
```

### Планы
```
Format: YYYY-MM-DD-feature-name.md
Location: workspace/active/orch-{id}/plan.md OR user's file

Examples:
- 2026-02-10-auth-system.md
- 2026-02-11-payment-integration.md
```

### ID задач (в плане)
```
Format: PREFIX-NNN

Префиксы:
- AUTH — аутентификация
- PAY — платежи
- API — API
- UI — UI
- DB — БД
- REF — рефакторинг

Examples:
- AUTH-001, AUTH-002
- PAY-001, PAY-002
- API-001
```

### Отчёты
```
Format: YYYY-MM-DD-feature-implementation.md
Location: {config.documentation.paths.reports}/

Examples:
- 2026-02-10-auth-implementation.md
- 2026-02-11-payment-implementation.md
```

### Issues (файлы)
```
Format: ISS-NNN-description.md
Location: {config.documentation.paths.issues}/

Examples:
- ISS-001-token-refresh-race.md
- ISS-002-add-2fa-support.md
```

---

## Связи в системе

```
Orchestration (1) → Plan (1) → Tasks (N) → Report (1)

Workspace (временный):
  .cursor/workspace/active/orch-2026-02-10-15-30-auth/
    ├── progress.json        [метаданные]
    ├── tasks.json           [статусы]
    └── links.json           [ссылки]
          ↓
Документация (постоянная):
  docs/plans/2026-02-10-auth-system.md      [plan content]
  docs/reports/2026-02-10-auth-report.md    [final report]
  docs/issues/ISS-001-token-race.md         [known issues]
```

---

## Пример полного цикла

### 1. Планирование
```
User: /orchestrate Build auth system

Planner:
→ Creates workspace: .cursor/workspace/active/orch-2026-02-10-15-30-auth/
→ Creates plan: docs/plans/2026-02-10-auth-system.md
→ Initializes: progress.json, tasks.json, links.json
→ Returns: "Ready to execute with 5 tasks"
```

### 2. Реализация
```
Orchestrator:
→ Loads workspace: orch-2026-02-10-15-30-auth
→ Reads plan from: docs/plans/2026-02-10-auth-system.md
→ Processes AUTH-001:
  - Updates: workspace/tasks.json (in-progress)
  - Updates: docs/plans/...md (🔄 In Progress)
  - Calls worker
  - Updates: workspace/tasks.json (completed)
  - Updates: docs/plans/...md (✅ Completed)
→ Processes AUTH-002:
  - Review finds minor issue
  - Creates: docs/issues/ISS-001-token-refresh-race.md
  - Continues (doesn't block)
→ ... continues with remaining tasks
```

### 3. Документация
```
Documenter:
→ Reads: workspace metadata + docs/plans/
→ Creates: docs/reports/2026-02-10-auth-implementation.md
→ Archives workspace: active/ → completed/
→ Auto-cleanup after 7 days (configurable)
```

### 4. Позже: закрытие issues
```
User: /orchestrate Fix known issues

Planner:
→ Reads: docs/issues/ISS-*.md (open issues)
→ Creates new orchestration: orch-2026-02-15-09-00-fixes
→ Creates: docs/plans/2026-02-15-fix-issues.md
```

---

## Преимущества

### ✅ Нет дублирования
```
Workspace = metadata only
Documentation = actual content
```

### ✅ Параллельные оркестрации
```
.cursor/workspace/active/
  orch-auth-123/      [изолированно]
  orch-payments-456/  [изолированно]
```

### ✅ Восстановление после сбоя
```
Состояние в workspace → можно продолжить  
Документация уже записана → без потери смысла
```

### ✅ Настраиваемые пути
```json
{
  "documentation": {
    "paths": {
      "plans": "specs/",           // GitHub Spec Kit
      "reports": "docs/adr/",      // ADR
      "issues": ".github/issues/"  // GitHub Issues
    }
  }
}
```

### ✅ Разделение
```
Временное: состояние задач (workspace)  
Постоянное: документация фич (пути из config)
```

---

## Индикаторы статусов

### Статус оркестрации
- 🔵 **planning** — составляется план
- 🟢 **ready** — план готов к выполнению
- 🟡 **in-progress** — выполняются задачи
- 🟠 **documenting** — пишется итоговый отчёт
- ✅ **completed** — всё готово
- ❌ **failed** — прервано / сбой

### Статус задачи
- ⏳ **pending** — не начата
- 🔄 **in-progress** — в работе
- ✅ **completed** — сделано и проверено
- 🚫 **blocked** — ждёт зависимость

### Серьёзность issue
- 🔴 **Critical** (P1) — сразу
- 🟠 **High** (P2) — на неделе
- 🟡 **Medium** (P3) — в месяце
- 🟢 **Low** (P4) — по возможности
- 🔵 **Enhancement** (P5) — улучшение

---

**Итог:** два уровня — временный workspace для состояния, постоянная документация для планов и отчётов.
