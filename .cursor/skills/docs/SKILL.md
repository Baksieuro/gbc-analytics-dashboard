---
name: docs
description: Структура документации проекта. Когда пользователь спрашивает про доки или как они устроены.
disable-model-invocation: false
---

# Skill: структура документации

## Документация из конфига

**ВАЖНО:** пути задаются в `.cursor/config.json`. Не хардкодь `ai_docs/` и другие корни.

### Чтение конфига

```javascript
config = readJSON(".cursor/config.json")
paths = config.documentation.paths
```

## Структура по умолчанию

Если корень `ai_docs/` (или свой из config):

```
{configured-root}/               # paths.root
├── design/                      # paths.design
├── develop/
│   ├── api/                     # paths.api
│   ├── architecture/            # paths.architecture
│   ├── components/              # paths.components
│   ├── features/                # paths.features
│   ├── plans/                   # paths.plans
│   ├── reports/                 # paths.reports
│   └── issues/                  # paths.issues
└── changelog/                   # paths.changelog
```

## Назначение каталогов

- **plans/** — что строить (planner)  
- **reports/** — что сделано (documenter)  
- **issues/** — техдолг (любой агент)  
- **features/** — описания фич  
- **api/** — эндпоинты  
- **components/** — компоненты  
- **architecture/** — решения и паттерны  
- **design/** — UI/UX  
- **changelog/** — версии  

## Когда обновлять

**Автоматически:** после оркестрации, фич, багфиксов, ADR.

**По запросу:** «обнови документацию», «задокументируй».

## Как читать доки в контексте

Доки могут быть в `.cursorignore`. Подставь `{root}` из config:

```
@{root}/develop/features/authentication.md
@{root}/develop/api/endpoints.md
@{root}
```

## Команды

- Упоминания documenter в workflow  
- `@{root}` — включить доку в контекст  

## Правила

1. Одна тема — один файл  
2. Даты обновлений  
3. Ссылки на реальные файлы кода  
4. Актуальность, архив устаревшего  
5. Markdown  
6. Перекрёстные ссылки  

## Именование

- Фичи: `feature-name.md` (kebab-case)  
- Компоненты: `ComponentName.md` (PascalCase)  
- Issues: `issue-123.md` или описательное имя  

## Примеры запросов пользователя

- Задокументируй фичу аутентификации  
- Обнови API-доки  
- Покажи открытые задачи в документации  
- Архивируй закрытые issues  
- Создай ADR про server components  

Пример фрагмента `config.json` — как в эталоне; пути можно менять под проект.
