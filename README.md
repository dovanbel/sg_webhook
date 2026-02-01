# ShotGrid Webhook Server - Docker Deployment

## Table of Contents
- [Quick Start](#quick-start)
- [GitHub Container Registry Setup](#github-container-registry-setup)
- [Logging](#logging)
- [Updating the Application](#updating-the-application)

## Quick Start

### 1. Setup Environment Variables

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your actual ShotGrid credentials.

### 2. Build and Run with Docker Compose

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

## GitHub Container Registry Setup

### Publishing to GitHub Container Registry (GHCR)

GitHub provides free Docker image hosting through GitHub Container Registry. Your images will be public by default when the repository is public.

#### Automated GitHub Actions (Recommended)

1. **Create the GitHub Actions workflow directory:**
   ```bash
   mkdir -p .github/workflows
   ```

2. **Copy the workflow file:**
   ```bash
   cp .github-workflows-docker-publish.yml .github/workflows/docker-publish.yml
   ```

3. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Add Docker and GitHub Actions workflow"
   git push
   ```

4. **The workflow will automatically:**
   - Build your Docker image on every push to `main`/`master`
   - Push it to `ghcr.io/YOUR_USERNAME/YOUR_REPO_NAME:latest`
   - Create versioned tags when you push git tags (e.g., `v1.0.0`)
   - Images are public by default (matching your repository visibility)

#### Manual Push (Alternative)

```bash
# Build the image
docker build -t shotgrid-webhook .

# Tag for GHCR (replace YOUR_USERNAME and YOUR_REPO_NAME)
docker tag shotgrid-webhook ghcr.io/YOUR_USERNAME/YOUR_REPO_NAME:latest

# Login to GHCR (use a Personal Access Token with 'write:packages' scope)
echo YOUR_GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# Push to GHCR
docker push ghcr.io/YOUR_USERNAME/YOUR_REPO_NAME:latest
```

### Using the Pre-built Image

Once your image is published to GHCR, update your `docker-compose.yml`:

```yaml
services:
  shotgrid-webhook:
    # Comment out the build section
    # build:
    #   context: .
    #   dockerfile: Dockerfile
    
    # Use the pre-built image from GHCR
    # Replace YOUR_USERNAME and YOUR_REPO_NAME
    image: ghcr.io/YOUR_USERNAME/YOUR_REPO_NAME:latest
    
    # Rest of the configuration...
```

Then deploy:

```bash
# Pull the latest image and restart (no authentication needed for public images)
docker-compose pull
docker-compose up -d
```

## Logging

The application now logs to both console (Docker logs) and a file with rotation.

### Log Configuration

- **Location:** `./logs/shotgrid_webhook.log` (on host)
- **Format:** `YYYY-MM-DD HH:MM:SS - logger_name - LEVEL - message`
- **Rotation:** Daily at midnight
- **Retention:** 7 days (one week)
- **Naming:** Rotated logs are named `shotgrid_webhook.log.YYYY-MM-DD`

### Viewing Logs

```bash
# View Docker console logs (stdout)
docker-compose logs -f

# View file logs (on host)
tail -f logs/shotgrid_webhook.log

# View older rotated logs
ls -lh logs/
cat logs/shotgrid_webhook.log.2024-01-15
```

### Log Volume

The logs are persisted in a volume mapped to `./logs` on your host machine. This means:
- Logs survive container restarts
- You can access logs directly from the host
- Logs are automatically cleaned up after 7 days

### Custom Log Location

To change the log directory, set the `LOG_DIR` environment variable:

```yaml
# docker-compose.yml
environment:
  - LOG_DIR=/custom/path
volumes:
  - ./my-logs:/custom/path
```

## Updating the Application

### When Using Local Build

When you modify your Python code:

```bash
# Rebuild and restart
docker-compose up -d --build
```

### When Using GHCR Image

1. **Update your code and push to GitHub:**
   ```bash
   git add .
   git commit -m "Updated webhook logic"
   git push
   ```

2. **GitHub Actions automatically builds and pushes** the new image

3. **On your deployment server, pull the latest image:**
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

### Version Tagging

For production deployments, use version tags:

```bash
# Tag a release
git tag v1.0.0
git push origin v1.0.0
```

This creates a tagged image: `ghcr.io/YOUR_USERNAME/shotgrid-webhook:1.0.0`

Update docker-compose to use specific version:
```yaml
image: ghcr.io/YOUR_USERNAME/shotgrid-webhook:1.0.0
```

## Development vs Production

### Development (Local)

Keep using your current setup with `.env` file:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 9222 --reload
```

Logs will go to both console and `./logs/shotgrid_webhook.log`.

### Production (Docker)

```bash
# Using pre-built image from GHCR
docker-compose pull
docker-compose up -d

# Monitor
docker-compose logs -f
```

## Environment Variables

Required variables:
- `SHOTGUN_SITE` - Your ShotGrid site URL
- `SHOTGUN_WEBHOOK_SCRIPT_USER` - Script user name
- `SHOTGUN_WEBHOOK_SCRIPT_KEY` - Script user API key
- `SHOTGUN_WEBHOOK_SECRET` - Webhook secret for signature verification
- `LOG_DIR` - (Optional) Log directory path (default: `/app/logs`)

## Troubleshooting

### View logs
```bash
# Container logs
docker-compose logs -f shotgrid-webhook

# File logs
tail -f logs/shotgrid_webhook.log
```

### Enter container shell
```bash
docker-compose exec shotgrid-webhook /bin/bash
```

### Check environment variables
```bash
docker-compose exec shotgrid-webhook env | grep SHOTGUN
```

### Check log rotation
```bash
# List all log files
ls -lh logs/

# The current log
ls -lh logs/shotgrid_webhook.log

# Older logs (will be cleaned up after 7 days)
ls -lh logs/shotgrid_webhook.log.*
```

### Permission Issues with Logs

If you encounter permission issues:

```bash
# On host, ensure the logs directory is writable
chmod 755 logs/
```

## Complete Deployment Workflow

### First Time Setup

```bash
# 1. Clone your repository
git clone https://github.com/YOUR_USERNAME/shotgrid-webhook.git
cd shotgrid-webhook

# 2. Setup environment
cp .env.example .env
# Edit .env with your credentials

# 3. Login to GHCR (for private images)
echo YOUR_GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# 4. Deploy
docker-compose pull
docker-compose up -d

# 5. Verify
docker-compose logs -f
```

### Updating Production

```bash
# 1. Pull latest changes
git pull

# 2. Pull latest Docker image
docker-compose pull

# 3. Restart with new image
docker-compose up -d

# 4. Verify
docker-compose logs -f
tail -f logs/shotgrid_webhook.log
```