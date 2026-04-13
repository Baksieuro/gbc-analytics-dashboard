---
name: git-helper
description: Помощник по Git: сообщения коммитов, ветки, конфликты, типовые сценарии workflow.
---

# Skill: Git helper

## Возможности

### 1. Сообщения коммитов
Проанализируй staged-изменения и сформируй сообщение в стиле Conventional Commits.

```bash
# Индексированные изменения
git diff --cached --stat
git diff --cached
```

**Формат Conventional Commits:**
```
<type>(<scope>): <subject>

<optional body>
```

**Типы:**
- `feat` — новая фича
- `fix` — исправление бага
- `refactor` — структура без смены поведения
- `docs` — только документация
- `test` — только тесты
- `chore` — инструменты, конфиги, зависимости
- `perf` — производительность

**Examples:**
```
feat(auth): add JWT token refresh
fix(api): handle null response in user endpoint
refactor(db): extract query builders to separate file
docs(readme): update installation steps
```

### 2. Ветки

**Создать feature-ветку:**
```bash
git checkout main
git pull origin main
git checkout -b feature/description
```

**Удалить слитые ветки:**
```bash
git branch --merged | grep -v "main\|master" | xargs git branch -d
```

**Обновить ветку с main:**
```bash
git fetch origin
git rebase origin/main
# OR
git merge origin/main
```

### 3. Конфликты

При конфликтах:
1. Identify conflicting files: `git status`
2. Open each file and look for conflict markers
3. Resolve by choosing correct code
4. Stage resolved files: `git add <file>`
5. Continue: `git rebase --continue` or `git commit`

### 4. Откат

**Последний коммит (изменения сохранить):**
```bash
git reset --soft HEAD~1
```

**Снять индексацию:**
```bash
git restore --staged <file>
```

**Отменить локальные правки:**
```bash
git restore <file>
```

**Откат уже запушенного (новый коммит):**
```bash
git revert <commit-hash>
```

### 5. История

**Когда появился баг:**
```bash
git bisect start
git bisect bad          # current commit is bad
git bisect good <hash>  # known good commit
# Git переключит на середину — тестируй: git bisect good/bad
```

**Кто менял строку:**
```bash
git blame <file>
```

**Поиск в сообщениях коммитов:**
```bash
git log --grep="keyword"
```

**Поиск в изменениях кода:**
```bash
git log -p -S "function_name"
```

### 6. Stash

**Временно спрятать работу:**
```bash
git stash push -m "description"
git stash list
git stash show stash@{0}
```

**Вернуть из stash:**
```bash
git stash pop       # apply and remove
git stash apply     # apply and keep
git stash drop      # discard
```

### 7. Теги (релизы)

**Создать и запушить:**
```bash
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0
git push origin --tags  # push all tags
```

**Список и удаление:**
```bash
git tag -l
git tag -d v1.0.0                    # локально
git push origin :refs/tags/v1.0.0    # удалённо
```

### 8. Cherry-pick

**Перенести коммит на текущую ветку:**
```bash
git cherry-pick <commit-hash>
git cherry-pick <hash1> <hash2>  # несколько коммитов
```

## Генерация сообщения коммита

Если просят сообщение коммита:

1. `git diff --cached --stat` — список файлов
2. `git diff --cached` — содержимое изменений
3. Тип по смыслу изменений:
   - новая фича/файл → `feat`
   - исправление бага → `fix`
   - реструктуризация без смены поведения → `refactor`
   - только тесты → `test`
   - документация → `docs`
   - зависимости, конфиги, инструменты → `chore`
4. Scope: компонент / сервис / область
5. Сообщение в формате Conventional Commits

## Типовые сценарии

### «Создать PR»
```bash
git push -u origin HEAD
gh pr create --title "feat: description" --body "..."
# или ссылка на создание PR в веб-интерфейсе
```

### «Squash коммитов»
```bash
git rebase -i HEAD~<number>
# В редакторе: pick → squash для объединяемых коммитов
```

**Внимание:** интерактивный rebase не на общих ветках.

### «Закоммитил не в ту ветку»
```bash
git log -1  # hash
git checkout correct-branch
git cherry-pick <hash>

# Убрать с неверной ветки
git checkout wrong-branch
git reset --hard HEAD~1
```

### «Merge vs Rebase»
- **Merge** — сохраняет историю, merge-коммит
- **Rebase** — линейная история, переписывает коммиты

Rebase: обновить feature от main, причесать локальные коммиты.  
Merge: влить фичу в main; общая ветка.

## Безопасность

- Не force push в `main`/`master`
- Не rebase общих веток
- Перед разрушительными операциями — бэкап/ветка
- Перед операцией — `git status`

**Примечание:** в проекте могут быть хуки в `.cursor/hooks/` (линт и т.д.).
