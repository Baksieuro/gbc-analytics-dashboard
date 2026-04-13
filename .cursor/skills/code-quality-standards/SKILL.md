---
name: code-quality-standards
description: Качество кода и рефакторинг. Читать refactor перед рефакторингом, reviewer при проверке, worker при написании кода, debugger при исправлениях.
---

# Skill: стандарты качества кода

**Назначение:** стандарты качества, практики и приёмы рефакторинга.

---

## Принципы качества

### 1. Читаемость

Код читают в разы чаще, чем пишут. Оптимизируй чтение.

#### Имена
```
// ✅ Good - Self-explanatory
function calculateMonthlyPayment(principal, rate, months)
  return (principal * rate) / (1 - pow(1 + rate, -months))

// ❌ Bad - Unclear
function calc(p, r, m)
  return (p * r) / (1 - pow(1 + r, -m))
```

#### Короткие функции
- Max 20-30 lines per function
- One level of abstraction per function
- Do one thing well

```
// ✅ Good - Small, focused
function validateEmail(email)
  return isValidEmailFormat(email)

function validatePassword(password)
  return length(password) >= 8 AND hasUpperCase(password) AND hasDigit(password)

function validateUser(user)
  return validateEmail(user.email) AND validatePassword(user.password)

// ❌ Bad - Too long, does multiple things
function validateUser(user)
  // 50+ lines of validation logic
```

---

### 2. DRY

#### Общая логика в одном месте
```
// ❌ Bad - Duplication
function getActiveUsers()
  return filter(users, u => u.status == 'active' AND u.deletedAt == null)

function getActivePosts()
  return filter(posts, p => p.status == 'active' AND p.deletedAt == null)

// ✅ Good - Extracted common logic
function isActive(item)
  return item.status == 'active' AND item.deletedAt == null

function getActiveUsers()
  return filter(users, isActive)

function getActivePosts()
  return filter(posts, isActive)
```

---

### 3. KISS

#### Простые решения
```
// ✅ Good - Simple and clear
function isEven(n)
  return n % 2 == 0

// ❌ Bad - Over-engineered
function isEven(n)
  return (n & 1 == 0) ? true : false
```

---

### 4. YAGNI

Не добавляй функциональность «на будущее» без запроса.

```
// ❌ Bad - Unused complexity
User:
  name
  email
  phone     // Maybe we'll need it later?
  fax       // Just in case?
  twitter   // Why not?

// ✅ Good - Only what's needed now
User:
  name
  email
```

---

## Запахи и рефакторинг

### 1. Длинный метод
**Запах:** функция > 30 строк  
**Рефакторинг:** разбить на меньшие функции

### 2. Большой класс
**Запах:** слишком много обязанностей  
**Рефакторинг:** разделить классы (SRP)

### 3. Длинный список параметров
**Запах:** 4+ параметра  
**Рефакторинг:** объект параметров или builder

```
// ❌ Bad
function createUser(name, email, age, address, phone)

// ✅ Good
CreateUserParams:
  name
  email
  age
  address
  phone

function createUser(params: CreateUserParams)
```

### 4. Дублирование
**Запах:** одинаковый код в нескольких местах  
**Рефакторинг:** общая функция/класс

### 5. Primitive obsession
**Запах:** примитивы вместо маленьких типов  
**Рефакторинг:** value objects

```
// ❌ Bad
function sendEmail(email: String)
  // No validation, easy to pass invalid email

// ✅ Good
Email:
  value: String
  
  constructor(emailString)
    if NOT isValidEmail(emailString)
      throw Error('Invalid email')
    this.value = emailString
  
  function isValidEmail(email)
    return matchesEmailPattern(email)
  
  function toString()
    return this.value

function sendEmail(email: Email)
  // Email is guaranteed to be valid
```

### 6. Feature envy
**Запах:** метод больше трогает чужие данные  
**Рефакторинг:** перенести метод

### 7. Мёртвый код
**Запах:** неиспользуемое  
**Рефакторинг:** удалить

---

## Практики

### 1. Ошибки

```
// ✅ Good - Specific error types
ValidationError extends Error:
  constructor(message)
    super(message)
    this.name = 'ValidationError'

try:
  validateUser(user)
catch error:
  if error is ValidationError:
    // Handle validation errors
  else:
    // Handle other errors

// ❌ Bad - Generic errors
try:
  validateUser(user)
catch error:
  log('Error:', error)
```

### 2. Null safety

```
// ✅ Good - Explicit null handling
function getUser(id): User or null
  return find(users, u => u.id == id) or null

user = getUser('123')
if user is not null:
  print(user.name)

// ❌ Bad - Implicit nulls
function getUser(id): User
  return find(users, u => u.id == id)

user = getUser('123')
print(user.name)  // Potential crash if null
```

### 3. Иммутабельность

```
// ✅ Good - Immutable (create new object)
updatedUser = copyWithChanges(user, { name: 'New Name' })

// ❌ Bad - Mutation (modify existing object)
user.name = 'New Name'
```

### 4. Чистые функции

```
// ✅ Good - Pure function
function add(a, b)
  return a + b

// ❌ Bad - Side effects
total = 0
function add(a, b)
  total = total + a + b  // Modifies external state
  return total
```

---

## Чеклист рефакторинга

Перед:
- [ ] Tests are in place (to verify behavior doesn't change)
- [ ] Code smell identified
- [ ] Refactoring technique chosen

Во время:
- [ ] Make small, incremental changes
- [ ] Run tests after each change
- [ ] Commit after each successful refactoring

После:
- [ ] All tests still pass
- [ ] Code is more readable
- [ ] Complexity reduced
- [ ] No new bugs introduced

---

## Метрики сложности

### Цикломатическая сложность
- **1-5**: Simple, low risk
- **6-10**: Moderate complexity
- **11-20**: High complexity, consider refactoring
- **21+**: Very high risk, must refactor

```
// High complexity (many branches)
function processOrder(order)
  if order.status == 'pending':
    if order.total > 1000:
      if order.customer.vip:
        // ...
      else:
        // ...
    else:
      // ...
  else if order.status == 'shipped':
    // ...
  // ... more branches

// Лучше: полиморфизм или strategy
```

---

## Чеклист ревью качества

### Читаемость
- [ ] Clear variable/function names
- [ ] Functions are small and focused
- [ ] Comments explain "why", not "what"
- [ ] Consistent formatting

### Сопровождение
- [ ] No code duplication
- [ ] Single Responsibility Principle
- [ ] Low coupling, high cohesion
- [ ] Easy to extend

### Корректность
- [ ] Edge cases handled
- [ ] Error handling implemented
- [ ] Input validation present
- [ ] Tests cover main scenarios

### Производительность
- [ ] No obvious bottlenecks
- [ ] Efficient algorithms used
- [ ] Database queries optimized
- [ ] Unnecessary work avoided

---

## Типовые приёмы рефакторинга

### Extract Method
Длинный метод → несколько коротких

### Rename
Понятные имена

### Magic number → константа
```
// Before: if (age > 18)
LEGAL_AGE = 18
if (age > LEGAL_AGE)
```

### Parameter Object
Длинные списки параметров → объект

### Условие → полиморфизм
if/switch → иерархия классов

---

## Ссылки

- [Clean Code by Robert C. Martin](https://www.oreilly.com/library/view/clean-code-a/9780136083238/)
- [Refactoring by Martin Fowler](https://refactoring.com/)
- [Code Smells Catalog](https://refactoring.guru/refactoring/smells)

---

**Примечание:** единообразно по кодовой базе; агенты ссылаются на skill при написании, ревью и рефакторинге.
