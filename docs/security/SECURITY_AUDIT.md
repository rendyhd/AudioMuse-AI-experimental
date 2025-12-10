# AudioMuse-AI Security Audit

## Executive Summary

AudioMuse-AI is designed for self-hosted, private network deployment. It does not implement authentication or authorization, relying on network-level security. This document identifies security considerations and recommendations.

## Security Model

### Design Assumptions
1. **Private Network Only**: Application runs on trusted network
2. **Single User**: No multi-tenancy or user isolation
3. **Trusted Media Server**: Media server credentials stored in environment
4. **Local AI Optional**: AI providers are external or self-hosted (Ollama)

## Authentication & Authorization

### Current State
- **No authentication**: All API endpoints are public
- **No authorization**: No role-based access control
- **No session management**: Stateless API design

### Recommendation
For public-facing deployments, implement reverse proxy authentication:
```nginx
location / {
    auth_basic "AudioMuse";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://audiomuse:8000;
}
```

## Input Validation

### API Endpoints
| Endpoint | Validation | Risk Level |
|----------|------------|------------|
| POST `/api/similarity/find` | Basic type checking | LOW |
| POST `/api/clustering/start` | Parameter bounds | LOW |
| POST `/api/chat/message` | None (passed to AI) | MEDIUM |
| POST `/api/analysis/start` | Basic type checking | LOW |

### SQL Injection Prevention
- **Parameterized queries**: All database queries use parameterized statements
- **psycopg2 Binary**: Bytea fields use `psycopg2.Binary()` wrapper

```python
# Good - Parameterized query
cur.execute("SELECT * FROM tracks WHERE item_id = %s", (item_id,))

# Not found in codebase - String formatting (vulnerable)
cur.execute(f"SELECT * FROM tracks WHERE item_id = '{item_id}'")
```

### Command Injection Prevention
- **No shell=True**: Subprocess calls use lists, not shell strings
- **FFmpeg**: Audio file paths passed as arguments, not shell-interpolated

```python
# Good - List arguments
subprocess.run(['ffmpeg', '-i', filepath, ...], shell=False)
```

## Sensitive Data Handling

### API Keys & Credentials
| Data | Storage | Risk |
|------|---------|------|
| Media server tokens | Environment variables | LOW - Not in code |
| AI provider API keys | Environment variables | LOW - Not in code |
| PostgreSQL password | Environment variables | LOW - Not in code |

### Recommendations
1. Never commit `.env` files to version control
2. Use Docker secrets for production deployments
3. Rotate API keys periodically

## Network Security

### Exposed Services
| Service | Default Port | Protocol |
|---------|--------------|----------|
| Flask Web | 8000 | HTTP |
| PostgreSQL | 5432 | TCP |
| Redis | 6379 | TCP |

### Recommendations
1. Do not expose PostgreSQL/Redis to public networks
2. Use HTTPS via reverse proxy (Nginx, Caddy, Traefik)
3. Enable `ENABLE_PROXY_FIX=true` when behind reverse proxy

## Third-Party Dependencies

### AI Provider Risks
- API keys sent to external services (Gemini, Mistral, OpenAI)
- Chat messages may contain sensitive data
- Rate limiting protects against accidental overuse

### Mitigation
- Use Ollama for fully local AI processing
- Set `AI_MODEL_PROVIDER=NONE` if AI features not needed

### Media Server Risks
- Full access tokens stored in environment
- Can create/modify playlists on media server
- Downloads audio files from server

### Mitigation
- Use read-only API tokens where possible
- Restrict library access via `MUSIC_LIBRARIES` setting

## Container Security

### Docker Image
- Base image: `python:3.11-slim`
- Non-root user recommended (not currently enforced)
- No secrets in image layers

### Recommendations
1. Run containers as non-root user
2. Use read-only file system where possible
3. Limit container capabilities

```yaml
# docker-compose.yaml additions
services:
  audiomuse:
    user: "1000:1000"
    read_only: true
    security_opt:
      - no-new-privileges:true
```

## Logging & Monitoring

### Current State
- Python logging to stdout
- Task status logged to database
- No centralized log management

### Sensitive Data in Logs
- API keys NOT logged
- File paths logged (may reveal directory structure)
- Media server responses may be logged

### Recommendations
1. Centralize logs (ELK stack, Loki)
2. Set log level to WARNING in production
3. Implement log rotation

## Known Vulnerabilities

### Low Priority
1. **No rate limiting**: API endpoints can be called unlimited times
   - Impact: Resource exhaustion
   - Mitigation: Network-level rate limiting

2. **Task ID enumeration**: Task IDs are UUIDs (unpredictable)
   - Impact: Low - Anyone on network can view task status
   - Mitigation: None needed for private networks

3. **Error message disclosure**: Stack traces may leak in development
   - Impact: Information disclosure
   - Mitigation: Set `FLASK_ENV=production`

### Medium Priority
1. **Unbounded AI prompts**: Chat messages passed directly to AI
   - Impact: Prompt injection possible
   - Mitigation: Prompt sanitization not implemented

## Security Checklist

### Pre-Deployment
- [ ] Remove default passwords from `.env`
- [ ] Restrict network access to Flask/Redis/PostgreSQL
- [ ] Configure reverse proxy with HTTPS
- [ ] Set `FLASK_ENV=production`
- [ ] Review AI provider API key permissions

### Ongoing
- [ ] Monitor AI API usage for anomalies
- [ ] Rotate API keys annually
- [ ] Update Docker images regularly
- [ ] Review logs for suspicious activity

## Incident Response

### Suspected Compromise
1. Rotate all API keys immediately
2. Check media server for unauthorized changes
3. Review Flask/RQ logs
4. Consider re-analyzing library if embeddings tampered

## Compliance Notes

- **GDPR**: No personal user data collected
- **PCI-DSS**: Not applicable (no payment processing)
- **HIPAA**: Not applicable (no health data)

## Security Contacts

For security issues, open a private issue on GitHub or contact the maintainers directly.
