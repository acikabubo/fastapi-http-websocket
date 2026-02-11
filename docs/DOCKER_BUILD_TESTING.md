# Docker Build Testing Guide

Quick reference for testing Docker builds before pushing to production.

## Quick Tests

### Option 1: Full Automated Test (Recommended)

```bash
make test-docker-build
```

**What it does:**
- ✅ Validates Docker is running
- ✅ Checks Dockerfile syntax
- ✅ Builds production image
- ✅ Verifies image size (warns if > 1GB)
- ✅ Tests container startup
- ✅ Checks health endpoint
- ✅ Scans logs for errors
- ✅ Runs security scan (if Trivy installed)
- ✅ Automatic cleanup

**Time:** 2-5 minutes

---

### Option 2: Quick Build Test

```bash
make build-prod
```

Just builds the image without validation tests.

**Time:** 1-3 minutes

---

### Option 3: Manual Build

```bash
docker build -f docker/Dockerfile.production -t fastapi-app:test .
```

**Time:** 1-3 minutes

---

## Detailed Testing Steps

### 1. Build the Image

```bash
docker build \
  -f docker/Dockerfile.production \
  -t fastapi-app:test \
  --progress=plain \
  .
```

### 2. Check Image Size

```bash
docker images fastapi-app:test

# Expected: ~300-400 MB
# Warning if: > 1 GB
```

### 3. Inspect Image Metadata

```bash
docker inspect fastapi-app:test --format='{{json .Config.Labels}}' | jq
```

Expected labels:
- `org.opencontainers.image.created`
- `org.opencontainers.image.revision`
- `org.opencontainers.image.version`

### 4. Test Container Startup

```bash
docker run -d \
  --name fastapi-test \
  -p 8001:8000 \
  -e ENV=production \
  -e DB_USER=test \
  -e DB_PASSWORD=test \
  -e DB_HOST=localhost \
  -e KEYCLOAK_REALM=test \
  -e KEYCLOAK_CLIENT_ID=test \
  -e KEYCLOAK_BASE_URL=http://localhost:8080 \
  -e KEYCLOAK_ADMIN_USERNAME=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  fastapi-app:test
```

### 5. Check Logs

```bash
# View startup logs
docker logs fastapi-test

# Follow logs
docker logs -f fastapi-test

# Check for errors
docker logs fastapi-test 2>&1 | grep -i error
```

### 6. Test Health Endpoint (if implemented)

```bash
curl http://localhost:8001/health
```

### 7. Cleanup

```bash
docker stop fastapi-test
docker rm fastapi-test
docker rmi fastapi-app:test
```

---

## Common Issues and Solutions

### Issue: Build Fails with "Cannot find module"

**Cause:** Missing dependency in `pyproject.toml`

**Solution:**
```bash
# Check pyproject.toml for missing packages
uv add <missing-package>
git add pyproject.toml
```

---

### Issue: Image Size > 1 GB

**Cause:** Unnecessary files included in image

**Solution:**
1. Check `.dockerignore` is excluding dev files
2. Verify multi-stage build is working:
   ```bash
   docker history fastapi-app:test
   ```
3. Look for large layers

---

### Issue: Container Exits Immediately

**Cause:** Startup error (missing env vars, DB connection)

**Solution:**
```bash
# Check logs
docker logs fastapi-test

# Common fixes:
# - Add missing environment variables
# - Check database connection settings
# - Verify Keycloak configuration
```

---

### Issue: "ModuleNotFoundError" at Runtime

**Cause:** Dependency installed in builder stage but not runtime stage

**Solution:**
Check `Dockerfile.production` - ensure dependencies are copied from builder:
```dockerfile
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
```

---

## Security Scanning

### Install Trivy (Optional but Recommended)

```bash
# macOS
brew install trivy

# Linux
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update
sudo apt-get install trivy
```

### Run Security Scan

```bash
# Scan image for vulnerabilities
trivy image fastapi-app:test

# Only high/critical vulnerabilities
trivy image --severity HIGH,CRITICAL fastapi-app:test

# Exit with error code if vulnerabilities found
trivy image --severity HIGH,CRITICAL --exit-code 1 fastapi-app:test
```

---

## GitHub Actions Workflow Testing

### Test Workflow Locally with `act`

```bash
# Install act (https://github.com/nektos/act)
brew install act  # macOS
# or see: https://github.com/nektos/act#installation

# Run workflow locally
act push --workflows .github/workflows/docker-build-push.yml

# Dry run (don't actually push)
act push --workflows .github/workflows/docker-build-push.yml --dryrun
```

### Test on Feature Branch

```bash
# Create test branch
git checkout -b test-docker-build

# Commit changes
git add .github/workflows/docker-build-push.yml docker/Dockerfile.production
git commit -m "test: Verify Docker build workflow"

# Push to trigger workflow (if workflow configured for all branches)
git push origin test-docker-build

# Check GitHub Actions: https://github.com/<username>/fastapi-http-websocket/actions
```

---

## Pre-Push Checklist

Before pushing to `main`:

- [ ] Run `make test-docker-build` successfully
- [ ] Check image size is reasonable (~300-400 MB)
- [ ] Verify container starts without errors
- [ ] Test health endpoint (if implemented)
- [ ] No critical security vulnerabilities (Trivy scan)
- [ ] `.dockerignore` excludes development files
- [ ] `Dockerfile.production` uses multi-stage build
- [ ] All environment variables documented

---

## Continuous Monitoring

After push to `main`:

1. **Watch GitHub Actions:**
   - Go to: https://github.com/<username>/fastapi-http-websocket/actions
   - Click on latest "Build and Push Docker Image" workflow
   - Monitor build progress

2. **Check Build Logs:**
   - Expand each step in GitHub Actions
   - Look for warnings or errors

3. **Verify Image Published:**
   - Go to: GitHub repo → Packages (right sidebar)
   - Check latest image is published
   - Verify tags are correct

4. **Test Pulling Image:**
   ```bash
   docker pull ghcr.io/<username>/fastapi-http-websocket:latest
   docker run -p 8000:8000 --env-file .env.production ghcr.io/<username>/fastapi-http-websocket:latest
   ```

---

## Performance Testing

### Build Time Optimization

```bash
# Measure build time
time docker build -f docker/Dockerfile.production -t fastapi-app:test .

# Use BuildKit for faster builds
DOCKER_BUILDKIT=1 docker build -f docker/Dockerfile.production -t fastapi-app:test .

# Enable build cache
docker build --cache-from fastapi-app:latest -f docker/Dockerfile.production -t fastapi-app:test .
```

### Image Size Optimization

```bash
# Analyze layers
docker history fastapi-app:test

# Find large files
docker run --rm fastapi-app:test du -sh /* 2>/dev/null | sort -h

# Compare with development image
docker images | grep fastapi
```

---

## Rollback Strategy

If production build fails after push:

1. **Revert to previous image:**
   ```bash
   docker pull ghcr.io/<username>/fastapi-http-websocket:main-<previous-sha>
   docker tag ghcr.io/<username>/fastapi-http-websocket:main-<previous-sha> ghcr.io/<username>/fastapi-http-websocket:latest
   docker push ghcr.io/<username>/fastapi-http-websocket:latest
   ```

2. **Revert commit:**
   ```bash
   git revert <commit-sha>
   git push origin main
   ```

3. **Fix and re-deploy:**
   ```bash
   # Fix Dockerfile.production
   git add docker/Dockerfile.production
   git commit -m "fix: Correct production Dockerfile"
   git push origin main
   ```

---

## Related Documentation

- [Docker Registry Setup](DOCKER_REGISTRY.md)
- [GitHub Container Registry Docs](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Dockerfile Best Practices](https://docs.docker.com/develop/dev-best-practices/)
