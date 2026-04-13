# Настройка агентов Cursor под проект

Скопируй нужный промпт ниже и вставь в чат Cursor.

---

## 1. Настройка test-writer

По умолчанию `test-writer` универсальный — он сам определяет стек и соглашения по существующим тестам в проекте. Но если хочешь зафиксировать конкретные инструкции (фреймворк, структура, моки), запусти этот промпт один раз. Агент добавит секцию `## Project-Specific Instructions` в начало `.cursor/agents/test-writer.md`, и при следующих вызовах он будет следовать именно ей, а не автоопределению.

```
Просканируй этот проект и настрой под него агента test-writer.

Шаги:
1. Определи технологический стек, проверив:
   - package.json (dependencies, devDependencies)
   - tsconfig.json (TypeScript)
   - pyproject.toml / setup.py / requirements.txt
   - go.mod
   - Cargo.toml
   - pom.xml / build.gradle
   - Gemfile
   - composer.json

2. Найди используемый тестовый фреймворк:
   - JS/TS: ищи jest, vitest, mocha, @testing-library/* в package.json
   - Python: ищи pytest, unittest в requirements / pyproject.toml
   - Go: проверь go.mod на github.com/stretchr/testify
   - Rust: проверь dev-dependencies в Cargo.toml
   - Java: проверь pom.xml / build.gradle на junit, mockito
   - Ruby: проверь Gemfile на rspec или minitest
   - PHP: проверь composer.json на phpunit

3. Проверь, есть ли в проекте тестовые файлы:
   - Ищи файлы по шаблонам: *.test.ts, *.spec.ts, *.test.js, *.spec.js,
     test_*.py, *_test.py, *_test.go, *_test.rs, *_spec.rb

--- ВЕТКА A: тесты уже есть ---

4a. Проанализируй существующие тесты и выведи соглашения проекта:
    - Именование файлов (*.test.ts vs *.spec.ts, test_*.py vs *_test.py и т.д.)
    - Расположение (рядом с исходниками vs папки tests/ / __tests__/)
    - Как настраиваются моки/стабы (jest.mock, vi.mock, pytest fixtures и т.д.)
    - Общие утилиты, фабрики или хелперы для тестов
    - Вложенность describe/it (JS/TS), table-driven стиль (Go) и т.д.
    - Найди 2–3 типичных существующих тестовых файла и прочитай их

5a. Отредактируй `.cursor/agents/test-writer.md`:
    - Добавь в самое начало тела файла (сразу после блока frontmatter) новую секцию:
      ## Project-Specific Instructions
      со следующим содержимым:
      - **Stack:** [обнаруженный язык + фреймворк]
      - **Test framework:** [конкретный фреймворк и версия, если известна]
      - **File naming:** [точный шаблон, напр. `*.test.ts`]
      - **File location:** [рядом с кодом / tests/ / __tests__/ и т.д.]
      - **Mock approach:** [как в этом проекте делаются моки]
      - **Test utilities:** [перечисли найденные общие хелперы, фикстуры, фабрики]
      - **Example reference:** [путь к 1–2 хорошим существующим тестам как образцу]
    - Остальное содержимое файла не меняй

--- ВЕТКА B: тестов не найдено ---

4b. Исходя из обнаруженного стека, предложи 2–4 подходящих тестовых фреймворка.
    Для каждого варианта укажи: название, команду установки, краткое обоснование.
    Пометь один вариант как ⭐ RECOMMENDED — тот, что лучше всего подходит стеку,
    экосистеме и сложности проекта.

    Примеры рекомендаций по стеку:
    - React/Next.js + TypeScript → ⭐ Vitest + @testing-library/react
      (быстрее Jest, нативный ESM, тот же API, из коробки с Vite)
    - Node.js backend (без бандлера) → ⭐ Jest или ⭐ Vitest
    - Python → ⭐ pytest (стандарт, богатая экосистема)
    - Go → ⭐ встроенное testing + testify
    - Rust → ⭐ встроенное #[cfg(test)]

5b. Спроси пользователя:
    "В проекте тестов не найдено. Вот варианты настройки тестирования:

    [перечисли варианты с ⭐ у рекомендуемого]

    Настроить один из них? Ответь номером или названием,
    или 'no' — пропустить и настроить агента с настройками по умолчанию."

6b. Если пользователь подтвердил выбор:
    - Установи нужные пакеты (напр. npm install -D vitest @testing-library/react)
    - При необходимости создай минимальный конфиг (vitest.config.ts, jest.config.ts, pytest.ini и т.д.)
    - Добавь скрипт test в package.json (или аналог), если его нет
    - Создай один минимальный пример теста, чтобы у агента было с чего брать соглашения
    - Затем отредактируй `.cursor/agents/test-writer.md` как в шаге 5a,
      опираясь на только что установленный фреймворк

Перед любыми правками покажи, что нашёл, чтобы я мог подтвердить.
```

---

## 2. Настройка test-runner

Агент просканирует структуру проекта и обновит `.cursor/agents/test-runner.md` — заменит дженерик-примеры на реальные команды для этого проекта.

```
Просканируй этот проект и настрой под него агента test-runner.

Шаги:
1. Определи технологический стек, проверив:
   - package.json (скрипты: test, lint, typecheck, build)
   - pyproject.toml / setup.py / requirements.txt
   - go.mod
   - Cargo.toml
   - Gemfile
   - composer.json
   - Makefile (цели `test`, `lint`, `check`)
   - Любой CI: .github/workflows/, .gitlab-ci.yml, Jenkinsfile

2. Найди тестовую инфраструктуру:
   - Раннер: jest, vitest, pytest, go test, cargo test, rspec, phpunit и т.д.
   - Папки с тестами: tests/, __tests__/, test/, spec/
   - Шаблоны имён: *.test.ts, *_test.go, test_*.py, *_spec.rb
   - Команды coverage, если настроены

3. Найди линтинг и статический анализ:
   - JS/TS: eslint, biome, oxlint (скрипты в package.json + конфиги .eslintrc*, biome.json)
   - Python: ruff, pylint, flake8, mypy (pyproject.toml, setup.cfg, ruff.toml)
   - Go: golangci-lint (.golangci.yml)
   - Rust: cargo clippy, cargo fmt --check
   - Ruby: rubocop
   - PHP: phpcs, phpstan, psalm
   - Проверка типов: tsc --noEmit, mypy, pyright

4. Выясни, как запускать только отдельные файлы/пакеты (не весь набор):
   - напр. `jest path/to/file`, `pytest tests/unit/test_foo.py`, `go test ./pkg/auth/...`

5. Отредактируй `.cursor/agents/test-runner.md`:
    - Замени общие примеры автоопределения в секциях "Linter Checks" и "Run Tests"
      на ТОЧНЫЕ команды для этого проекта
    - Добавь в начало (после frontmatter) секцию:
      ## Project-Specific Commands
      с конкретными командами по категориям (lint, typecheck, test all, test single file/package, coverage)
    - Остальное содержимое файла не меняй

Перед правками покажи, что нашёл, чтобы я мог подтвердить.
```
