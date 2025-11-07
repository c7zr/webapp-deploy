# Instagram Report Bot - Security Checklist

## Pre-Deployment Security Checklist

### 1. Dependencies & CVEs
- [ ] Run `pip install --upgrade pip`
- [ ] Run `pip install --upgrade -r requirements.txt`
- [ ] Run `pip-audit` to check for known vulnerabilities
  ```bash
  pip install pip-audit
  pip-audit
  ```
- [ ] Run `safety check` for additional CVE scanning
  ```bash
  pip install safety
  safety check
  ```

### 2. Database Security
- [ ] **CRITICAL**: Move database to separate server (NOT same host as web app)
- [ ] Use PostgreSQL or MySQL instead of SQLite for production
- [ ] Database server behind firewall, only accessible from web server
- [ ] Use strong database passwords (20+ characters)
- [ ] Enable database encryption at rest
- [ ] Regular automated backups to secure location
- [ ] Restrict database user permissions (principle of least privilege)

### 3. Application Security
- [ ] Change SECRET_KEY in .env (use `openssl rand -hex 32`)
- [ ] Enable HTTPS only (no HTTP)
- [ ] Set proper CORS_ORIGINS (whitelist only)
- [ ] Review all API endpoints for authentication requirements
- [ ] Enable rate limiting on all endpoints
- [ ] Implement request size limits
- [ ] Add CSP (Content Security Policy) headers
- [ ] Enable HSTS (HTTP Strict Transport Security)

### 4. Infrastructure Security
- [ ] Database on separate server from web application
- [ ] Use reverse proxy (nginx/caddy) in front of application
- [ ] Configure firewall rules (only port 80/443 open)
- [ ] Enable fail2ban for brute force protection
- [ ] Regular OS security updates
- [ ] Use non-root user to run application
- [ ] Disable SSH password auth (use keys only)

### 5. Monitoring & Logging
- [ ] Set up log monitoring (failed logins, errors, etc.)
- [ ] Configure alerts for suspicious activity
- [ ] Regular security log reviews
- [ ] Monitor for unusual database queries
- [ ] Track API usage patterns

### 6. Code Security
- [ ] Remove all debug statements
- [ ] Remove all console.log in production
- [ ] Sanitize all user inputs
- [ ] Use parameterized queries (already done)
- [ ] Validate all file uploads
- [ ] Remove unused dependencies

## Quick Security Commands

### Check for vulnerabilities:
```bash
# Install security tools
pip install pip-audit safety

# Check for CVEs
pip-audit
safety check

# Update all packages
pip install --upgrade -r requirements.txt
```

### Generate secure secret key:
```bash
# Linux/Mac
openssl rand -hex 32

# Windows PowerShell
python -c "import secrets; print(secrets.token_hex(32))"
```

### Production Database Setup (PostgreSQL example):
```bash
# Install PostgreSQL client
pip install psycopg2-binary

# Update .env with external database
DATABASE_TYPE=postgresql
DATABASE_HOST=db-server.example.com  # DIFFERENT SERVER
DATABASE_PORT=5432
DATABASE_NAME=instagram_report_bot
DATABASE_USER=app_user
DATABASE_PASSWORD=your-strong-password
```

## Common CVE Fixes

### FastAPI/Uvicorn
```bash
pip install --upgrade fastapi uvicorn
```

### Cryptography
```bash
pip install --upgrade cryptography
```

### PyJWT
```bash
pip install --upgrade pyjwt
```

## Production Deployment Example

### Using Docker with separate database:
```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_HOST=db-server.external.com  # External DB!
      - DATABASE_TYPE=postgresql
    depends_on:
      - redis

  redis:
    image: redis:alpine
    # No database here - use external managed database service
```

### Recommended: Use managed database services
- AWS RDS (PostgreSQL/MySQL)
- Google Cloud SQL
- Azure Database
- DigitalOcean Managed Databases

**NEVER run database on same server as web application in production!**

## Regular Maintenance Schedule

- **Daily**: Check error logs
- **Weekly**: Review security logs, check for failed login attempts
- **Monthly**: Update dependencies, run security scans
- **Quarterly**: Full security audit, penetration testing

## If You Find a Vulnerability

1. Immediately update affected package
2. Review logs for exploitation attempts
3. Notify users if data may be compromised
4. Document incident and response

## Additional Resources

- OWASP Top 10: https://owasp.org/www-project-top-ten/
- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
- Python Security: https://python.readthedocs.io/en/stable/library/security_warnings.html
