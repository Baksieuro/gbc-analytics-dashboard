---
name: security-guidelines
description: Безопасность: практики и чеклисты. Читать security-auditor перед аудитом, worker при auth/API/данных, debugger при security-фиксах, reviewer при проверке.
---

# Skill: руководство по безопасности

**Назначение:** стандарты и практики безопасности проекта.

## Базовые принципы

### 1. Аутентификация и авторизация

#### ✅ Делай:
- Use bcrypt/argon2 for password hashing (never MD5/SHA1)
- Implement rate limiting on auth endpoints
- Use secure session management (httpOnly, secure cookies)
- Implement CSRF protection for state-changing operations
- Use JWT with short expiration times (15 min access, 7 days refresh)
- Store refresh tokens securely (encrypted in DB)

#### ❌ Не делай:
- Never store passwords in plain text or reversible encryption
- Don't expose user IDs in URLs (use UUIDs)
- Don't trust client-side validation alone
- Don't implement your own crypto (use established libraries)

```typescript
// ✅ Good
import bcrypt from 'bcrypt';
const hash = await bcrypt.hash(password, 10);

// ❌ Bad
import crypto from 'crypto';
const hash = crypto.createHash('md5').update(password).digest('hex');
```

---

### 2. Валидация и санитизация ввода

#### ✅ Делай:
- Validate all user input on the server
- Use allowlists, not denylists
- Sanitize HTML input (DOMPurify for client, sanitize-html for server)
- Validate file uploads (type, size, content)
- Use parameterized queries for SQL (never string concatenation)

#### ❌ Не делай:
- Don't trust any client-side data
- Don't use `eval()` or `Function()` on user input
- Don't execute user-provided code

```typescript
// ✅ Good - Parameterized query
const user = await db.query(
  'SELECT * FROM users WHERE email = $1',
  [email]
);

// ❌ Bad - SQL injection risk
const user = await db.query(
  `SELECT * FROM users WHERE email = '${email}'`
);
```

---

### 3. Безопасность API

#### ✅ Делай:
- Use HTTPS everywhere (enforce TLS 1.2+)
- Implement rate limiting (per IP, per user)
- Validate Content-Type headers
- Use CORS properly (don't use `*` in production)
- Return generic error messages (don't leak implementation details)
- Log security events (failed logins, permission denials)

#### ❌ Не делай:
- Don't expose stack traces in production
- Don't return sensitive data in error messages
- Don't use predictable API keys or tokens

```typescript
// ✅ Good - Generic error
res.status(401).json({ error: 'Invalid credentials' });

// ❌ Bad - Leaks information
res.status(401).json({ error: 'User exists but password is wrong' });
```

---

### 4. Секреты

#### ✅ Делай:
- Use environment variables for secrets
- Use secret management tools (AWS Secrets Manager, Vault)
- Rotate secrets regularly
- Use different secrets for dev/staging/prod
- Add `.env` to `.gitignore`

#### ❌ Не делай:
- Never commit secrets to Git
- Don't hardcode API keys in code
- Don't log secrets (passwords, tokens, API keys)

```typescript
// ✅ Good
const apiKey = process.env.API_KEY;

// ❌ Bad
const apiKey = "sk_live_12345abcdef";
```

---

### 5. Защита данных

#### ✅ Делай:
- Encrypt sensitive data at rest (PII, payment info)
- Use HTTPS for data in transit
- Implement proper access control (RBAC/ABAC)
- Minimize data collection (GDPR compliance)
- Implement secure data deletion

#### ❌ Не делай:
- Don't store sensitive data unnecessarily
- Don't log sensitive information
- Don't share data without user consent

---

### 6. Зависимости и supply chain

#### ✅ Делай:
- Regularly update dependencies (`npm audit`, `yarn audit`)
- Use lock files (package-lock.json, yarn.lock)
- Review dependencies before adding
- Use tools like Snyk or Dependabot
- Pin versions in production

#### ❌ Не делай:
- Don't use outdated packages with known vulnerabilities
- Don't install packages from untrusted sources
- Don't use `npm install` without reviewing what's being added

---

### 7. Фронтенд

#### ✅ Делай:
- Implement Content Security Policy (CSP) headers
- Use Subresource Integrity (SRI) for CDN resources
- Escape/sanitize user content before rendering
- Use framework's built-in XSS protection (React auto-escapes)
- Validate data on frontend AND backend
- Use secure storage (never localStorage for tokens)

#### ❌ Не делай:
- Don't use `dangerouslySetInnerHTML` without sanitization
- Don't store sensitive data in localStorage/sessionStorage
- Don't trust client-side validation alone
- Don't disable CSP or use `unsafe-inline` in production

```typescript
// ✅ Good - CSP header
res.setHeader('Content-Security-Policy', 
  "default-src 'self'; script-src 'self' https://trusted-cdn.com");

// ✅ Good - Sanitize before rendering
import DOMPurify from 'dompurify';
const clean = DOMPurify.sanitize(userInput);

// ❌ Bad - XSS risk
<div dangerouslySetInnerHTML={{ __html: userInput }} />
```

---

### 8. Современная аутентификация

#### ✅ Делай:
- Use OAuth 2.0 / OpenID Connect for third-party auth
- Implement PKCE for public clients (SPAs, mobile)
- Use secure redirect URI validation
- Implement Multi-Factor Authentication (MFA)
- Store OAuth tokens securely (httpOnly cookies or encrypted)

#### ❌ Не делай:
- Don't use implicit flow (deprecated)
- Don't expose client secrets in frontend code
- Don't skip redirect URI validation
- Don't implement your own OAuth server (use Auth0, Keycloak, etc.)

```typescript
// ✅ Good - OAuth with PKCE
const { codeVerifier, codeChallenge } = generatePKCE();
const authUrl = `${provider}/authorize?code_challenge=${codeChallenge}`;

// ✅ Good - MFA check
if (user.mfaEnabled && !req.session.mfaVerified) {
  return res.status(401).json({ error: 'MFA required' });
}
```

---

### 9. Платформенная специфика

#### GraphQL
- Implement query depth limiting
- Add query complexity analysis
- Use persisted queries in production
- Disable introspection in production

```typescript
// ✅ Good - Query depth limit
const depthLimit = require('graphql-depth-limit');
const server = new ApolloServer({
  validationRules: [depthLimit(5)]
});
```

#### WebSocket
- Authenticate on connection and per-message
- Implement rate limiting per connection
- Validate origin header
- Use secure WebSocket (wss://)

```typescript
// ✅ Good - WebSocket auth
wss.on('connection', (ws, req) => {
  const token = new URL(req.url, 'wss://base').searchParams.get('token');
  if (!verifyToken(token)) {
    ws.close(4401, 'Unauthorized');
  }
});
```

#### Server-Sent Events (SSE)
- Require authentication for SSE endpoints
- Validate event data before sending
- Implement connection limits per user

---

## Чеклист безопасности

### Фича аутентификации
- [ ] Passwords hashed with bcrypt/argon2
- [ ] Rate limiting on login endpoint
- [ ] Session management secure (httpOnly cookies)
- [ ] CSRF protection enabled
- [ ] Password reset with secure tokens
- [ ] Account lockout after failed attempts

### API-эндпоинт
- [ ] Input validation on all parameters
- [ ] Authentication required (unless public)
- [ ] Authorization checks for resources
- [ ] Rate limiting configured
- [ ] CORS configured properly
- [ ] Generic error messages
- [ ] Security headers set (CSP, X-Frame-Options, etc.)

### Работа с БД
- [ ] Parameterized queries used
- [ ] SQL injection prevented
- [ ] Sensitive data encrypted
- [ ] Access control enforced
- [ ] Audit logging enabled

### Загрузка файлов
- [ ] File type validation
- [ ] File size limits
- [ ] Virus scanning (if applicable)
- [ ] Secure storage location
- [ ] Access control on files

---

## OWASP Top 10 (кратко)

### 1. Injection
**Профилактика:** параметризованные запросы, валидация, ORM

### 2. Broken Authentication
**Профилактика:** политика паролей, MFA, сессии

### 3. Утечки чувствительных данных
**Профилактика:** шифрование, минимизация сбора

### 4. XXE
**Профилактика:** отключить внешние сущности XML

### 5. Broken Access Control
**Профилактика:** deny by default, проверки на сервере, логи

### 6. Небезопасная конфигурация
**Профилактика:** минимальная конфигурация, сканирование, без дефолтов

### 7. XSS
**Профилактика:** экранирование, CSP, санитизация

### 8. Небезопасная десериализация
**Профилактика:** не десериализовать недоверенные данные

### 9. Уязвимые компоненты
**Профилактика:** обновления, скан зависимостей

### 10. Слабое логирование и мониторинг
**Профилактика:** события безопасности, алерты

---

## Тестирование безопасности

### Перед деплоем:
1. Run `npm audit` / `yarn audit`
2. Check for hardcoded secrets (grep, git-secrets)
3. Test authentication/authorization flows
4. Verify input validation
5. Review error handling
6. Check HTTPS enforcement

---

## Ссылки

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [CWE Top 25](https://cwe.mitre.org/top25/)

---

**Примечание:** агенты читают skill до реализации или ревью чувствительных к безопасности частей.
