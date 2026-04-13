---
description: Формат Conventional Commits для единообразных сообщений коммитов
globs: []
---

# Формат сообщения коммита

Используй формат [Conventional Commits](https://www.conventionalcommits.org/).

## Структура

```
<type>(<scope>): <subject>

[optional body]
```

## Типы

| Тип | Описание | Пример |
|------|----------|--------|
| `feat` | Новая фича | `feat(auth): add OAuth login` |
| `fix` | Исправление бага | `fix(api): handle null response` |
| `docs` | Документация | `docs: update API readme` |
| `refactor` | Изменение кода без фичи/фикса | `refactor: extract validation` |
| `test` | Тесты | `test: add auth unit tests` |
| `chore` | Обслуживание | `chore: update dependencies` |
| `perf` | Производительность | `perf: cache user queries` |
| `style` | Только форматирование | `style: fix indentation` |

## Правила

### Subject (заголовок)

- строчные буквы, без точки в конце
- повелительное наклонение: «add», не «added» / «adds»
- не длиннее 50 символов
- дополняет фразу: «This commit will…»

### Scope (опционально)

- область: `auth`, `api`, `ui`, `db`
- компонент: `button`, `header`, `user-service`

## Примеры

```bash
feat(cart): add quantity selector
fix(checkout): prevent double submission
refactor(db): extract query builders
docs(readme): update installation steps
```

## Когда использовать skill git-helper

**Используй `.cursor/skills/git-helper/SKILL.md`, когда:**

- пользователь просит сгенерировать сообщение коммита
- пользователь просит закоммитить изменения
- нужно проанализировать индексированные изменения и составить сообщение
- нужно выбрать тип коммита по смыслу изменений
