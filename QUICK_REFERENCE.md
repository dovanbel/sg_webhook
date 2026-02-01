# Quick Reference Guide

## GitHub Container Registry (GHCR) - Quick Commands

### Setup GitHub Actions (One-Time)
```bash
mkdir -p .github/workflows
cp .github-workflows-docker-publish.yml .github/workflows/docker-publish.yml
git add .
git commit -m "Add GitHub Actions workflow"
git push
```

**Note:** Images are public by default when your GitHub repository is public.

### Login to GHCR (Only needed for pushing)
```bash
# Create a Personal Access Token at https://github.com/settings/tokens
# Scope needed: write:packages (for pushing images)

echo YOUR_GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin
```

### Pull and Deploy (No login needed for public images)
```bash
docker-compose pull
docker-compose up -d
```

## Logging - Quick Commands

### View Logs
```bash
# Live container logs (stdout)
docker-compose logs -f

# Live file logs
tail -f logs/shotgrid_webhook.log

# View last 100 lines
tail -n 100 logs/shotgrid_webhook.log

# View older rotated logs
cat logs/shotgrid_webhook.log.2024-02-01
```

### Log Files
- Current: `logs/shotgrid_webhook.log`
- Rotated: `logs/shotgrid_webhook.log.YYYY-MM-DD`
- Retention: 7 days (automatically deleted after)
- Rotation: Daily at midnight

### Check Log Space
```bash
# See all log files and sizes
ls -lh logs/

# Total size
du -sh logs/
```

## Docker Compose Cheat Sheet

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Rebuild and restart
docker-compose up -d --build

# Pull latest images
docker-compose pull

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f shotgrid-webhook

# Execute command in container
docker-compose exec shotgrid-webhook bash

# Check status
docker-compose ps

# Remove everything (including volumes)
docker-compose down -v
```

## Update Workflows

### Local Development → Production

```bash
# 1. Test locally
uv run uvicorn main:app --host 0.0.0.0 --port 9222 --reload

# 2. Commit changes
git add .
git commit -m "Update webhook logic"
git push

# 3. GitHub Actions automatically builds image

# 4. On production server
docker-compose pull
docker-compose up -d
docker-compose logs -f
```

### Create a Version Release

```bash
# 1. Tag release
git tag v1.0.0
git push origin v1.0.0

# 2. GitHub Actions builds tagged image

# 3. Update docker-compose.yml to use specific version
# image: ghcr.io/YOUR_USERNAME/shotgrid-webhook:1.0.0

# 4. Deploy
docker-compose pull
docker-compose up -d
```

## Troubleshooting

### Verify Security (Production)
```bash
# Docs should be disabled (404)
curl -I http://localhost:9222/docs

# Health check should work (200)
curl -I http://localhost:9222/health

# Test webhook requires valid signature
curl -X POST http://localhost:9222/sg_task_webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
# Should return 401 (Missing signature)
```

### Container won't start
```bash
# Check logs
docker-compose logs shotgrid-webhook

# Check if port is in use
sudo lsof -i :9222

# Restart everything
docker-compose down
docker-compose up -d
```

### Can't pull image
```bash
# Verify image exists (check your GitHub repo's Packages section)
# Public images don't require authentication

# If pushing, re-login to GHCR
echo YOUR_GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# Try pull again
docker-compose pull
```

### Logs not appearing
```bash
# Check volume mount
docker-compose exec shotgrid-webhook ls -la /app/logs/

# Check permissions
ls -ld logs/

# Restart container
docker-compose restart
```

### Environment variables not working
```bash
# Check .env file exists
ls -la .env

# Check variables in container
docker-compose exec shotgrid-webhook env | grep SHOTGUN

# Restart after .env changes
docker-compose down
docker-compose up -d
```

## File Structure

```
shotgrid-webhook/
├── .env                          # Secrets (git ignored)
├── .env.example                  # Template
├── .gitignore                    # Git ignore rules
├── docker-compose.yml            # Orchestration config
├── Dockerfile                    # Image build instructions
├── main.py                       # FastAPI server
├── payload_processor.py          # Webhook logic with logging
├── pyproject.toml               # Python dependencies
├── logs/                        # Log files (git ignored)
│   ├── shotgrid_webhook.log    # Current log
│   └── shotgrid_webhook.log.*  # Rotated logs
└── .github/
    └── workflows/
        └── docker-publish.yml   # CI/CD workflow
```
