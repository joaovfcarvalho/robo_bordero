# Security Policy

## Reporting Security Issues

If you discover a security vulnerability, please email the maintainers directly instead of opening a public issue.

## Security Best Practices

### 1. Admin Password

⚠️ **CRITICAL**: Change the default admin password before deploying to production!

**Default password** (`cbf2025admin`) is for **development only**.

#### How to set a secure password:

**Railway:**
```bash
# In Railway dashboard, set environment variable:
ADMIN_PASSWORD=your-very-secure-password-here
```

**Docker/Docker Compose:**
```bash
# Create .env file:
echo "ADMIN_PASSWORD=your-very-secure-password-here" >> .env

# Or set in environment:
export ADMIN_PASSWORD=your-very-secure-password-here
docker-compose up -d
```

**Local Development:**
```bash
# Add to .env file:
ADMIN_PASSWORD=your-dev-password
```

### 2. API Keys

Never commit API keys to git. Always use environment variables:

- ✅ `ANTHROPIC_API_KEY` - From environment
- ✅ `SUPABASE_SERVICE_KEY` - From environment
- ❌ Hardcoded in source code

### 3. CORS Configuration

In production, set specific origins instead of `*`:

```bash
# Development (default)
CORS_ORIGINS=*

# Production (specific domains)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 4. Supabase Security

Enable Row Level Security (RLS) in your Supabase project:

1. Go to your Supabase dashboard
2. Navigate to "Authentication" → "Policies"
3. Enable RLS on all tables
4. Create policies for:
   - Public read access for `jogos_resumo` (if needed)
   - Service role full access

### 5. HTTPS Only

Always use HTTPS in production:

- Railway provides automatic HTTPS
- For custom deployments, use Let's Encrypt or similar

### 6. Database Credentials

Protect your Supabase service role key:

- ✅ Use environment variables
- ✅ Never commit to git
- ✅ Rotate periodically (every 90 days recommended)
- ❌ Don't expose in frontend code

### 7. Token Security

The application uses in-memory token storage. For production:

- Tokens expire after 24 hours
- Consider Redis for token storage (multi-server deployments)
- Implement token refresh mechanism if needed

### 8. Rate Limiting

Consider adding rate limiting for production:

```python
# Example using slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/admin/login")
@limiter.limit("5/minute")
async def login(...):
    ...
```

### 9. Secrets Scanning

GitGuardian scans this repository for secrets. If flagged:

1. **Review the alert** - Is it a real secret or a false positive?
2. **For real secrets**:
   - Immediately revoke the exposed secret
   - Generate a new secret
   - Update all services using the secret
   - Consider rewriting git history (if not yet pushed)
3. **For false positives** (like default dev passwords):
   - Add security warnings in code
   - Document in this file
   - Consider ignoring in `.gitguardian.yaml`

### 10. Dependency Updates

Keep dependencies updated:

```bash
# Python
pip install --upgrade -r requirements.txt

# Node.js
cd frontend && npm update
```

## Security Checklist for Production

Before deploying to production, verify:

- [ ] Changed default admin password (`ADMIN_PASSWORD` set)
- [ ] All API keys are in environment variables
- [ ] CORS is configured for specific origins
- [ ] HTTPS is enabled
- [ ] Supabase RLS policies are enabled
- [ ] Database credentials are secure
- [ ] No secrets committed to git
- [ ] Dependencies are up to date
- [ ] Monitoring is set up
- [ ] Backups are enabled (Supabase)
- [ ] Rate limiting is configured (optional)

## Known "Secrets" (Not Actually Secrets)

The following are flagged by GitGuardian but are **not real secrets**:

1. **`cbf2025admin`** - Default development password
   - **Purpose**: Fallback for local development
   - **Not a security risk**: Documented to be changed in production
   - **Location**: `src/api/auth.py`, `docker-compose.yml`, `.env.example`
   - **Mitigation**: Application logs warning when using default password

## Security Features

✅ **JWT Token Authentication**
- Tokens expire after 24 hours
- Secure token generation using `secrets.token_urlsafe()`
- Constant-time password comparison

✅ **Protected Endpoints**
- Admin endpoints require valid JWT token
- Token verified on every request
- Auto-logout on token expiration

✅ **Environment-Based Secrets**
- All sensitive data from environment variables
- No hardcoded credentials in source code

✅ **CORS Protection**
- Configurable allowed origins
- Credentials support

✅ **Input Validation**
- Pydantic models validate all API inputs
- Type checking prevents injection attacks

## Reporting

For security issues, contact:
- Email: [your-email]
- GitHub Security Advisories: Enable in repository settings

## Updates

This security policy was last updated: 2025-01-11

We review and update security practices regularly.
