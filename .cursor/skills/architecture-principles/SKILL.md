---
name: architecture-principles
description: Архитектура и паттерны. Читать senior-reviewer перед архревью, planner при декомпозиции, worker при новых модулях, reviewer для согласованности.
---

# Skill: принципы архитектуры

**Назначение:** стандарты архитектуры и проектирования для проекта.

---

## Базовые принципы

### 1. SOLID

#### Single Responsibility (SRP)
- One class/module = one reason to change
- Separate concerns (data, logic, presentation)

```
// ✅ Good - Single responsibility
UserRepository:
  findById(id)  // DB logic only

UserService:
  validateUser(user)  // Business logic only

// ❌ Bad - Multiple responsibilities
User:
  save()      // DB logic
  validate()  // Business logic
  render()    // Presentation — three reasons to change
```

#### Open/Closed (OCP)
- Open for extension, closed for modification
- Use interfaces, abstract classes, composition

#### Liskov Substitution (LSP)
- Subtypes must be substitutable for base types
- Don't break parent class contracts

#### Interface Segregation (ISP)
- Many specific interfaces > one general interface
- Clients shouldn't depend on unused methods

#### Dependency Inversion (DIP)
- Depend on abstractions, not concretions
- High-level modules shouldn't depend on low-level modules

---

### 2. Разделение ответственности

#### Слоистая архитектура

```
┌─────────────────────────────┐
│   Presentation Layer        │  UI, Views, User Interface
├─────────────────────────────┤
│   Application Layer         │  Use Cases, Application Logic
├─────────────────────────────┤
│   Domain Layer              │  Business Logic, Entities
├─────────────────────────────┤
│   Data Layer                │  Data Access, Storage
├─────────────────────────────┤
│   Infrastructure Layer      │  External Services, I/O
└─────────────────────────────┘
```

**Правила:**
- Each layer only depends on layers below
- Business logic independent of infrastructure
- Easy to test each layer in isolation
- Upper layers depend on abstractions, not implementations

---

### 3. Паттерны проектирования

#### Repository
Абстракция доступа к данным: бизнес-логика не зависит от хранилища.

```
// Contract — what operations are available
UserRepository (interface/protocol/trait):
  findById(id) → User or null
  save(user)
  delete(id)

// Concrete implementation — one per storage backend
DatabaseUserRepository implements UserRepository:
  constructor(db)
  findById(id) → db.query("SELECT ... WHERE id = ?", id)
  save(user)   → db.exec("INSERT OR UPDATE ...", user)

// Business logic only knows the interface, not the implementation
UserService:
  constructor(repo: UserRepository)  // injected
```

#### Service
Инкапсулирует бизнес-логику и оркестрирует зависимости.

```
UserService:
  constructor(userRepo, notificationService)

  registerUser(data):
    1. validateRegistrationData(data)       // guard
    2. user = buildUserFromInput(data)      // domain logic
    3. userRepo.save(user)                  // persistence
    4. notificationService.sendWelcome(user) // side effect
    return user
```

#### Factory
Создание объектов без жёсткой привязки к классу в месте вызова.

```
PaymentProcessorFactory:
  create(type):
    if type == "stripe" → return StripeProcessor()
    if type == "paypal" → return PayPalProcessor()
    else → raise UnknownProcessorError(type)
```

#### Strategy
Взаимозаменяемые алгоритмы за общим интерфейсом.

```
// Contract
ValidationStrategy (interface):
  validate(value) → bool

// Implementations
EmailValidation implements ValidationStrategy:
  validate(email) → matchesEmailPattern(email)

PasswordValidation implements ValidationStrategy:
  validate(password) → length >= 8 AND hasUpperCase AND hasDigit

// Usage — caller doesn't know which strategy is used
Validator:
  constructor(strategy: ValidationStrategy)
  check(value) → strategy.validate(value)
```

---

### 4. Внедрение зависимостей

**Плюсы:**
- Loose coupling
- Easy testing (swap real deps for mocks/fakes)
- Flexible configuration

```
// ✅ Good - dependencies come in from outside
UserController:
  constructor(userService, logger)  // injected — easy to test/swap

// ❌ Bad - dependencies created internally
UserController:
  constructor():
    this.userService = new UserService()   // hardcoded — hard to test
    this.logger     = new ConsoleLogger()  // hardcoded — hard to swap
```

---

### 5. Обработка ошибок

#### Централизация

Типы ошибок предметной области вместо общих — вызывающий код обрабатывает кейсы явно.

```
// Domain error types (name them after what went wrong)
ValidationError(message, field?)   extends BaseError
NotFoundError(resource, id)        extends BaseError
UnauthorizedError(message)         extends BaseError

// Central handler dispatches by type
ErrorHandler:
  handle(error):
    if error is ValidationError  → respond 400, show field
    if error is NotFoundError    → respond 404
    if error is UnauthorizedError → respond 401
    else                         → respond 500, log details privately
    log(error.type, error.message)
```

---

### 6. Конфигурация

```
// ✅ Good - one place to read all config (env vars, files, flags)
config:
  environment    = env("APP_ENV", default="development")
  storage.type   = env("STORAGE_TYPE", default="local")
  logging.level  = env("LOG_LEVEL", default="info")
  features.maxRetries = env("MAX_RETRIES", default=3)

// ❌ Bad - config scattered across modules
// storage.go:    storageType = env("STORAGE_TYPE")
// logger.py:     logLevel    = env("LOG_LEVEL")
// retry.ts:      maxRetries  = env("MAX_RETRIES")
// → hard to find all config keys, easy to forget defaults
```

---

## Организация кода

### По фичам
Лучше для крупных приложений с относительно независимыми фичами

```
src/
├── features/
│   ├── authentication/
│   │   ├── auth.service.ts
│   │   ├── auth.store.ts
│   │   ├── auth.types.ts
│   │   └── auth.utils.ts
│   ├── users/
│   │   ├── user.service.ts
│   │   ├── user.types.ts
│   │   └── user.utils.ts
│   └── notifications/
├── shared/
│   ├── components/
│   ├── utils/
│   └── types/
└── config/
```

**Плюсы:**
- Features are self-contained
- Easy to find related code
- Can scale teams by feature
- Easy to remove/add features

### По слоям
Для меньших проектов или когда важнее технические слои, чем фичи

```
src/
├── services/
├── repositories/
├── models/
├── utils/
└── types/
```

**Плюсы:**
- Clear technical boundaries
- Easier to enforce layer rules
- Good for smaller codebases
- Simple to understand

---

## Производительность

### 1. Доступ к данным
- Index frequently accessed data
- Implement pagination for large datasets
- Use connection pooling for external resources
- Avoid N+1 queries (fetch related data efficiently)
- Lazy load data when appropriate

### 2. Кеширование
- Cache expensive computations
- Use appropriate cache invalidation strategies
- Consider memory vs speed tradeoffs
- Cache at the right layer (application, data, CDN)

### 3. Асинхронность
- Use async/await for I/O operations
- Don't block the main thread
- Implement background jobs for heavy tasks
- Use queues/streams for decoupling
- Consider parallelization opportunities

### 4. Ресурсы
- Clean up resources (connections, file handles, timers)
- Implement proper timeout mechanisms
- Use object pooling for expensive resources
- Monitor memory usage and prevent leaks

---

## Стратегия тестирования

### Пирамида

```
        /\
       /  \    E2E Tests (few)
      /----\
     /      \  Integration Tests (some)
    /--------\
   /          \ Unit Tests (many)
  /____________\
```

### Что тестировать:
- **Unit**: Business logic, utilities, pure functions, algorithms
- **Integration**: Component interactions, data flow, external services
- **E2E**: Critical user flows, main scenarios

---

## Антипаттерны

### ❌ God Object
Класс, который знает и делает слишком много

### ❌ Spaghetti Code
Запутанный поток без структуры

### ❌ Magic Numbers
Магические числа без смысла
```
// ❌ Bad
if user.age > 18 { ... }

// ✅ Good
MINIMUM_AGE = 18
if user.age > MINIMUM_AGE { ... }
```

### ❌ Циклические зависимости
A→B→A

### ❌ Преждевременная оптимизация
Без замеров узких мест

---

## Чеклист архитектурного ревью

### Структура
- [ ] Clear separation of concerns
- [ ] Consistent folder structure
- [ ] Logical module boundaries

### Зависимости
- [ ] No circular dependencies
- [ ] Dependency injection used
- [ ] Abstractions over concretions

### Масштабирование
- [ ] Components/services are stateless where possible
- [ ] Data access is optimized (indexed, cached)
- [ ] Resource usage is efficient
- [ ] System can handle increased load

### Сопровождение
- [ ] Code is self-documenting
- [ ] Consistent naming conventions
- [ ] Easy to add new features

### Тестируемость
- [ ] Business logic isolated
- [ ] Dependencies can be mocked
- [ ] Test coverage adequate

---

## Когда менять архитектуру

Признаки:

1. **Adding features is increasingly difficult**
2. **Changes in one area break unrelated areas**
3. **Tests are hard to write or brittle**
4. **Code duplication everywhere**
5. **Performance issues at scale**

---

## Ссылки

- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Design Patterns: Elements of Reusable Object-Oriented Software](https://en.wikipedia.org/wiki/Design_Patterns)

---

**Примечание:** агенты опираются на этот skill при архитектурных решениях и ревью дизайна системы.
