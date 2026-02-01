# Security Considerations

## Overview

This document outlines the security measures implemented for the ShotGrid webhook server.

## Key Security Features

### 1. **Webhook Signature Verification**

All incoming webhooks are verified using HMAC-SHA1 signatures:

```python
def verify_signature(body: bytes, received_signature: str) -> bool:
    expected_signature = "sha1=" + hmac.new(
        secret_key, body, hashlib.sha1
    ).hexdigest()
    return hmac.compare_digest(expected_signature, received_signature)
```

- ✅ Prevents unauthorized webhook calls
- ✅ Uses constant-time comparison to prevent timing attacks
- ✅ Rejects requests with missing or invalid signatures

### 2. **API Documentation Disabled in Production**

The `/docs`, `/redoc`, and `/openapi.json` endpoints are **disabled in production** to prevent:

- Information disclosure about API structure
- Exposure of endpoint parameters
- Interactive API testing by unauthorized users

**How it works:**
- Environment variable `ENVIRONMENT=production` disables docs
- Local development: docs remain enabled when `ENVIRONMENT=development` or unset
- Production (Docker): docs automatically disabled

**Testing:**
```bash
# Production (should return 404)
curl http://your-server:9222/docs
curl http://your-server:9222/redoc
curl http://your-server:9222/openapi.json

# Health check (should work)
curl http://your-server:9222/health
```

### 3. **Health Check Endpoint**

A dedicated `/health` endpoint provides monitoring without revealing sensitive information:

```json
GET /health
→ {"status": "healthy"}
```

- ✅ Safe for public monitoring systems
- ✅ Doesn't expose API structure
- ✅ Used by Docker health checks

### 4. **Environment Variables for Secrets**

All sensitive credentials are stored as environment variables:

- `SHOTGUN_WEBHOOK_SECRET` - Webhook signature verification
- `SHOTGUN_WEBHOOK_SCRIPT_KEY` - ShotGrid API key
- `SHOTGUN_SITE` - ShotGrid site URL
- `SHOTGUN_WEBHOOK_SCRIPT_USER` - Script user name

**Never commit:**
- `.env` files (git-ignored)
- Secrets in code
- API keys in logs

### 5. **Minimal Attack Surface**

The server only exposes necessary endpoints:

**Production:**
- `POST /sg_task_webhook` - Protected by signature verification
- `GET /health` - Safe, minimal information

**Development only:**
- `GET /docs` - FastAPI interactive docs
- `GET /redoc` - Alternative documentation
- `GET /openapi.json` - OpenAPI schema

### 6. **Log Security**

Logs are configured to avoid exposing sensitive data:

- Secrets are wrapped in `SecretStr` (Pydantic)
- Passwords/keys never printed in logs
- Log files are git-ignored
- Only application logs are persisted

## Production Deployment Checklist

Before deploying to production:

- [ ] Set `ENVIRONMENT=production` in docker-compose or environment
- [ ] Verify `/docs` returns 404
- [ ] Verify `/health` returns 200
- [ ] Test webhook signature verification works
- [ ] Ensure `.env` is not committed to git
- [ ] Use strong, unique values for `SHOTGUN_WEBHOOK_SECRET`
- [ ] Regularly rotate API keys
- [ ] Monitor logs for unauthorized access attempts
- [ ] Use HTTPS/TLS for all webhook traffic (configure reverse proxy)

## Additional Security Recommendations

### 1. **Use a Reverse Proxy**

Deploy behind nginx or similar to add:

- HTTPS/TLS termination
- Rate limiting
- IP whitelisting (only allow ShotGrid IPs)
- Additional security headers

```

### 2. **Rate Limiting**

Consider adding rate limiting to prevent abuse:

```python
# Example using slowapi
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/sg_task_webhook")
@limiter.limit("60/minute")  # Max 60 requests per minute
async def sg_task_webhook(...):
    ...
```

### 3. **Monitoring and Alerting**

Monitor for:
- Failed signature verification attempts
- Unusual traffic patterns
- Error rate spikes
- Disk space (for logs)

### 4. **Regular Updates**

Keep dependencies updated:

```bash
# Check for updates
uv pip list --outdated

# Update dependencies
uv pip install --upgrade <package>

# Rebuild Docker image
docker-compose up -d --build
```

## Testing Security

### Test 1: Verify Docs are Disabled

```bash
# Should return 404 in production
curl -I http://localhost:9222/docs
curl -I http://localhost:9222/redoc
curl -I http://localhost:9222/openapi.json

# Should return 200
curl -I http://localhost:9222/health
```

### Test 2: Verify Signature Validation

```bash
# Without signature (should fail)
curl -X POST http://localhost:9222/sg_task_webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# With invalid signature (should fail)
curl -X POST http://localhost:9222/sg_task_webhook \
  -H "Content-Type: application/json" \
  -H "x-sg-signature: sha1=invalid" \
  -d '{"test": "data"}'
```

### Test 3: Verify Environment Variable Handling

```bash
# Check that secrets are not exposed
docker-compose exec shotgrid-webhook env | grep SHOTGUN

# Verify SecretStr masking
docker-compose logs | grep -i "key\|secret"
# Should not see actual secret values
```

## Incident Response

If you suspect a security breach:

1. **Immediately rotate credentials:**
   - Generate new `SHOTGUN_WEBHOOK_SECRET`
   - Update ShotGrid webhook configuration
   - Generate new ShotGrid API keys
   - Update `.env` and redeploy

2. **Review logs:**
   ```bash
   # Check for suspicious activity
   grep "Invalid ShotGrid signature" logs/shotgrid_webhook.log
   grep "401" logs/shotgrid_webhook.log
   ```

3. **Update access:**
   - Review who has access to your deployment server
   - Check GitHub repository access
   - Verify GitHub Container Registry access

4. **Document and learn:**
   - Document what happened
   - Update security measures
   - Consider additional protections

## Questions or Concerns?

Security is an ongoing process. Regularly review and update these measures as your deployment evolves.
