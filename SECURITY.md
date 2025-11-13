# 🔐 Security Checklist for Production

## ✅ Pre-Deployment Security Checklist

### 1. Environment Variables
- [ ] .env файл НЕ в Git репозиторії
- [ ] .env додано в .gitignore
- [ ] API ключі НЕ в коді
- [ ] Усі секрети в Render Environment Variables
- [ ] SECRET_KEY згенеровано (мінімум 32 символи)
- [ ] SESSION_SECRET згенеровано (мінімум 32 символи)
- [ ] ADMIN_PASSWORD змінено з дефолтного (мінімум 8 символів)

### 2. Authentication & Authorization
- [ ] JWT автентифікація увімкнена
- [ ] Токени мають expiration (24 години)
- [ ] Паролі хешуються (bcrypt)
- [ ] Захищені endpoints вимагають токен
- [ ] Admin endpoints вимагають admin права

### 3. API Security
- [ ] Rate limiting увімкнено (60/хв, 1000/год)
- [ ] CORS налаштовано для конкретних доменів
- [ ] Input validation на всіх endpoints
- [ ] Output sanitization
- [ ] Error messages не розкривають внутрішні деталі

### 4. Database Security
- [ ] PostgreSQL з паролем
- [ ] IP whitelist налаштовано
- [ ] SQL injection захист (параметризовані запити)
- [ ] Regular backups налаштовано
- [ ] Sensitive data не логується

### 5. Network Security
- [ ] HTTPS only (Render надає автоматично)
- [ ] Trusted Host middleware увімкнено
- [ ] Security headers налаштовано
- [ ] GZip compression увімкнено

### 6. Logging & Monitoring
- [ ] Structured logging увімкнено
- [ ] Sensitive data не логується
- [ ] Error tracking налаштовано
- [ ] Health checks працюють
- [ ] Metrics збираються

### 7. Code Security
- [ ] No hardcoded secrets
- [ ] Dependencies updated (pip list --outdated)
- [ ] Vulnerability scanning (Trivy в CI/CD)
- [ ] Code review перед merge
- [ ] Tests покривають security scenarios

---

## 🚨 Critical Security Issues to Fix

### 1. Remove .env from Git History

```powershell
# Якщо .env був закомічений:
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

git push origin --force --all
```

### 2. Rotate Compromised Keys

Якщо API ключі були в Git:

1. **Google AI Studio**: https://makersuite.google.com/app/apikey
   - Видаліть старий ключ
   - Створіть новий
   - Оновіть в Render Environment Variables

2. **OpenAI**: https://platform.openai.com/api-keys
   - Revoke compromised key
   - Create new key
   - Update in Render

3. **Regenerate SECRET_KEY and SESSION_SECRET**:
   ```powershell
   -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})
   ```

---

## 🛡️ Security Best Practices

### 1. Regular Updates

```powershell
# Щотижня перевіряйте оновлення:
pip list --outdated

# Оновлюйте критичні security patches:
pip install --upgrade package-name

# Перезапустіть на Render
```

### 2. Monitor Logs

```bash
# Перевіряйте на підозрілу активність:
- Багато 401 (unauthorized)
- Багато 429 (rate limit)
- Дивні IP адреси
- SQL injection спроби
```

### 3. Database Backups

```bash
# Render Dashboard → brainai-db
- Manual Backup: Щотижня
- Automatic Backups: Увімкнено (Paid plan)
```

### 4. API Key Rotation

```bash
# Кожні 90 днів:
1. Створіть новий API ключ
2. Оновіть в Render Environment Variables
3. Протестуйте
4. Видаліть старий ключ
```

---

## 🔍 Security Testing

### 1. Authentication Testing

```powershell
# Спроба без токена (має бути 401):
curl https://your-app.onrender.com/api/metrics

# Спроба з невалідним токеном:
curl -H "Authorization: Bearer invalid_token" \
  https://your-app.onrender.com/api/metrics

# Спроба з валідним токеном (має бути 200):
curl -H "Authorization: Bearer $VALID_TOKEN" \
  https://your-app.onrender.com/api/metrics
```

### 2. Rate Limiting Testing

```powershell
# Швидкі запити (має бути 429 після ліміту):
for ($i=1; $i -le 70; $i++) {
    curl https://your-app.onrender.com/health
}
```

### 3. SQL Injection Testing

```powershell
# Спроба SQL injection (має бути блоковано):
curl -X POST https://your-app.onrender.com/process \
  -H "Content-Type: application/json" \
  -d '{"text": "'; DROP TABLE users; --", "archetype": "test"}'
```

---

## 📋 Incident Response Plan

### Якщо виявлено витік ключів:

1. **Негайно**:
   - [ ] Revoke/Delete compromised keys
   - [ ] Generate new keys
   - [ ] Update in Render
   - [ ] Restart service
   - [ ] Check logs для підозрілої активності

2. **Протягом години**:
   - [ ] Change all passwords
   - [ ] Rotate SECRET_KEY, SESSION_SECRET
   - [ ] Review database для несанкціонованих змін
   - [ ] Notify affected users (якщо є)

3. **Протягом дня**:
   - [ ] Full security audit
   - [ ] Review Git history
   - [ ] Update security documentation
   - [ ] Implement additional monitoring

### Контакти для екстрених ситуацій:

- **Render Support**: support@render.com
- **Google Cloud Support**: https://cloud.google.com/support
- **OpenAI Support**: https://help.openai.com

---

## ✅ Monthly Security Review

### Чек-лист для щомісячної перевірки:

- [ ] Review logs для підозрілої активності
- [ ] Check for outdated dependencies
- [ ] Review access logs
- [ ] Test backups
- [ ] Review rate limiting metrics
- [ ] Check for new security advisories
- [ ] Test disaster recovery plan
- [ ] Review and rotate API keys (кожні 3 місяці)

---

## 📚 Security Resources

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **FastAPI Security**: https://fastapi.tiangolo.com/tutorial/security/
- **Render Security**: https://render.com/docs/security
- **Python Security**: https://python.readthedocs.io/en/stable/library/security_warnings.html

---

**Пам'ятайте**: Безпека - це процес, а не одноразова подія!
