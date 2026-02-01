# Docker Build Troubleshooting Guide

## Common Build Issues and Solutions

### 1. Git Executable Not Found

**Error:**
```
Git executable not found. Ensure that Git is installed and available.
```

**Cause:** Your dependencies (like `sgtk` - ShotGrid Toolkit) are installed from git repositories, which requires git to be available during the build.

**Solution:** The Dockerfile now includes git installation in the builder stage:
```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*
```

**Why multi-stage?** We install git in the `builder` stage but don't include it in the final image, keeping the final image smaller and more secure.

---

### 2. uv.lock File Missing

**Error:**
```
error: Failed to find `uv.lock`
```

**Solution:** 
If you don't have a `uv.lock` file yet, either:

**Option A:** Generate one locally:
```bash
uv lock
git add uv.lock
git commit -m "Add uv.lock"
git push
```

**Option B:** Modify Dockerfile to not require frozen dependencies:
```dockerfile
# Change this line:
RUN uv sync --frozen --no-install-project --no-dev

# To this (less safe, but works without lock file):
RUN uv sync --no-install-project --no-dev
```

---

### 3. Permission Denied During Build

**Error:**
```
permission denied while trying to connect to the Docker daemon socket
```

**Solution:**
```bash
# Make sure Docker is running
sudo systemctl start docker

# Add your user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker

# Or use sudo
sudo docker build -t shotgrid-webhook .
```

---

### 4. Network Issues (Can't Pull Base Images)

**Error:**
```
failed to solve: failed to fetch
```

**Solution:**
```bash
# Check Docker Hub connectivity
docker pull python:3.11-slim

# If behind proxy, configure Docker:
# Create/edit ~/.docker/config.json
{
  "proxies": {
    "default": {
      "httpProxy": "http://proxy.example.com:8080",
      "httpsProxy": "http://proxy.example.com:8080"
    }
  }
}
```

---

### 5. Build Context Too Large

**Error:**
```
Sending build context to Docker daemon 500MB
```

**Solution:** Make sure you're using `.dockerignore`:
```bash
# Verify .dockerignore exists
cat .dockerignore

# Should exclude:
# - .venv/
# - __pycache__/
# - logs/
# - .git/
```

---

### 6. GitHub Actions Build Fails

**Error:**
```
GitHub Actions: permission denied to github-actions[bot]
```

**Solution:** Ensure the workflow has correct permissions in `.github/workflows/docker-publish.yml`:
```yaml
permissions:
  contents: read
  packages: write  # Required for pushing to GHCR
```

---

### 7. Out of Disk Space

**Error:**
```
no space left on device
```

**Solution:**
```bash
# Clean up Docker
docker system prune -a
docker volume prune

# Check disk space
df -h
```

---

### 8. Dependency Installation Fails

**Error:**
```
error: Failed to download distribution for package
```

**Possible causes:**
1. Network issues
2. Package not available for your Python version
3. Missing system dependencies

**Solution:**
```bash
# Test locally first
uv sync

# If it works locally, the issue is in Docker
# Add any missing system packages to Dockerfile:
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        build-essential \  # For packages that need compilation
        && rm -rf /var/lib/apt/lists/*
```

---

## Testing the Build Locally

Before pushing to GitHub, test the build locally:

```bash
# Build the image
docker build -t shotgrid-webhook-test .

# If successful, test run it
docker run --rm \
  -p 9222:9222 \
  -e SHOTGUN_SITE="https://test.shotgunstudio.com" \
  -e SHOTGUN_WEBHOOK_SCRIPT_USER="test" \
  -e SHOTGUN_WEBHOOK_SCRIPT_KEY="test" \
  -e SHOTGUN_WEBHOOK_SECRET="test" \
  shotgrid-webhook-test

# Test the endpoints
curl http://localhost:9222/health
curl -I http://localhost:9222/docs  # Should be 404 in production
```

---

## Debugging Build Steps

To see exactly where the build fails:

```bash
# Build with no cache (forces rebuild of all layers)
docker build --no-cache -t shotgrid-webhook .

# Build with progress output
docker build --progress=plain -t shotgrid-webhook .

# Build up to a specific stage
docker build --target builder -t shotgrid-webhook-builder .

# Inspect the builder stage
docker run --rm -it shotgrid-webhook-builder /bin/bash
```

---

## Checking Build Logs on GitHub Actions

1. Go to your repository on GitHub
2. Click "Actions" tab
3. Click on the failed workflow run
4. Click on the "build-and-push" job
5. Expand the failed step to see detailed logs

**Common GitHub Actions specific issues:**

- **Rate limiting:** Docker Hub may rate limit pulls. Solution: Authenticate or use mirrors
- **Timeout:** Large builds may timeout. Solution: Optimize Dockerfile, use caching
- **Secrets:** Make sure repository secrets are set if using private registries

---

## Getting More Help

If you encounter an issue not covered here:

1. Check the full error message carefully
2. Search for the error on GitHub Issues for the relevant tools (Docker, uv, etc.)
3. Enable debug logging:
   ```bash
   docker build --progress=plain --no-cache -t shotgrid-webhook . 2>&1 | tee build.log
   ```
4. Review `build.log` for the exact failure point
