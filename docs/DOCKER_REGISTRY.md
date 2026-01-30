# Docker Registry Setup

This document explains how to build, push, and deploy Docker images from the GitHub Container Registry.

## Overview

The project is configured to automatically build and push production Docker images to GitHub Container Registry (GHCR) when code is pushed to the `main` branch.

**Workflow:** `.github/workflows/docker-build-push.yml`
**Production Dockerfile:** `docker/Dockerfile.production`
**Registry:** `ghcr.io`

## Automatic Builds

### Triggers

Docker images are automatically built and pushed when:

1. **Code is pushed to `main` branch**
   - Creates image tagged as `latest`
   - Creates image tagged with commit SHA: `main-<sha>`

2. **Version tags are pushed** (e.g., `v1.0.0`, `v2.1.3`)
   - Creates semver tags: `1.0.0`, `1.0`, `1`
   - Example: pushing `v1.2.3` creates tags `1.2.3`, `1.2`, and `1`

3. **Manual workflow dispatch**
   - Go to Actions → "Build and Push Docker Image" → "Run workflow"

### Image Tags

The workflow creates multiple tags for each build:

```bash
# Main branch
ghcr.io/<username>/fastapi-http-websocket:latest
ghcr.io/<username>/fastapi-http-websocket:main
ghcr.io/<username>/fastapi-http-websocket:main-<sha>

# Version tags (e.g., v1.2.3)
ghcr.io/<username>/fastapi-http-websocket:1.2.3
ghcr.io/<username>/fastapi-http-websocket:1.2
ghcr.io/<username>/fastapi-http-websocket:1
```

## Manual Build and Push

### Prerequisites

1. **GitHub Personal Access Token** (if pushing manually):
   - Go to GitHub → Settings → Developer settings → Personal access tokens
   - Generate token with `write:packages` scope
   - Save token securely

2. **Docker installed** on your machine

### Build Production Image

```bash
# Build production image locally
docker build -f docker/Dockerfile.production -t fastapi-app:local .

# Test the image
docker run -p 8000:8000 --env-file .env.production fastapi-app:local
```

### Push to GHCR Manually

```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u <username> --password-stdin

# Tag image
docker tag fastapi-app:local ghcr.io/<username>/fastapi-http-websocket:manual

# Push image
docker push ghcr.io/<username>/fastapi-http-websocket:manual
```

## Pulling Images

### Public Repository

If your repository is public, anyone can pull the image:

```bash
docker pull ghcr.io/<username>/fastapi-http-websocket:latest
```

### Private Repository

For private repositories, authenticate first:

```bash
# Login with GitHub token
echo $GITHUB_TOKEN | docker login ghcr.io -u <username> --password-stdin

# Pull image
docker pull ghcr.io/<username>/fastapi-http-websocket:latest
```

## Deployment

### Docker Compose Production

Create `docker-compose.production.yml`:

```yaml
version: '3.8'

services:
  app:
    image: ghcr.io/<username>/fastapi-http-websocket:latest
    ports:
      - "8000:8000"
    env_file:
      - .env.production
    depends_on:
      - postgres
      - redis
      - keycloak
    restart: unless-stopped

  postgres:
    image: postgres:13
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:alpine
    restart: unless-stopped

  keycloak:
    image: quay.io/keycloak/keycloak:latest
    environment:
      KEYCLOAK_ADMIN: ${KEYCLOAK_ADMIN_USERNAME}
      KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD}
    command: start-dev
    ports:
      - "8080:8080"
    restart: unless-stopped

volumes:
  postgres_data:
```

Deploy:

```bash
# Pull latest image
docker pull ghcr.io/<username>/fastapi-http-websocket:latest

# Start services
docker-compose -f docker-compose.production.yml up -d

# View logs
docker-compose -f docker-compose.production.yml logs -f app
```

### Kubernetes Deployment

Create `k8s/deployment.yml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fastapi-app
  template:
    metadata:
      labels:
        app: fastapi-app
    spec:
      containers:
      - name: app
        image: ghcr.io/<username>/fastapi-http-websocket:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENV
          value: "production"
        envFrom:
        - secretRef:
            name: fastapi-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: fastapi-app
spec:
  selector:
    app: fastapi-app
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

Deploy to Kubernetes:

```bash
# Create secrets
kubectl create secret generic fastapi-secrets \
  --from-env-file=.env.production

# Deploy application
kubectl apply -f k8s/deployment.yml

# Check status
kubectl get pods
kubectl logs -f deployment/fastapi-app
```

## Image Optimization

### Multi-Stage Build

The production Dockerfile uses multi-stage builds to minimize image size:

1. **Builder stage**: Installs dependencies
2. **Runtime stage**: Copies only necessary files

**Benefits:**
- Smaller image size (no build tools in final image)
- Faster deployment (less data to transfer)
- Reduced attack surface (fewer packages)

### Size Comparison

```bash
# Development image
docker/Dockerfile: ~1.2 GB

# Production image
docker/Dockerfile.production: ~350 MB (70% smaller)
```

## Registry Management

### View Published Images

1. Go to your GitHub repository
2. Click "Packages" (right sidebar)
3. View all published versions and tags

### Delete Old Images

```bash
# List all tags
docker images ghcr.io/<username>/fastapi-http-websocket

# Delete specific tag locally
docker rmi ghcr.io/<username>/fastapi-http-websocket:old-tag

# Delete from registry (requires GitHub token with delete:packages scope)
# Via GitHub UI: Packages → Select image → Settings → Delete
```

### Image Retention Policy

Configure in `.github/workflows/docker-build-push.yml` (optional):

```yaml
- name: Delete old container images
  uses: snok/container-retention-policy@v2
  with:
    image-names: fastapi-http-websocket
    cut-off: 30 days ago UTC
    keep-at-least: 5
    account-type: personal
    token: ${{ secrets.GITHUB_TOKEN }}
```

## Troubleshooting

### Build Failures

**Check GitHub Actions logs:**
1. Go to repository → Actions
2. Click failed workflow run
3. Expand failed step to view errors

**Common issues:**
- Missing dependencies in `pyproject.toml`
- Incorrect Dockerfile path
- Permission denied (check workflow permissions)

### Push Failures

**Authentication error:**
```bash
# Verify GITHUB_TOKEN has write:packages permission
# Check repository settings → Actions → General → Workflow permissions
```

**Image too large:**
```bash
# Check .dockerignore excludes unnecessary files
# Verify multi-stage build is working correctly
```

### Pull Failures

**Unauthorized error:**
```bash
# Login first
echo $GITHUB_TOKEN | docker login ghcr.io -u <username> --password-stdin

# Or set package visibility to public in package settings
```

## Alternative Registries

### Docker Hub

Update `.github/workflows/docker-build-push.yml`:

```yaml
env:
  REGISTRY: docker.io
  IMAGE_NAME: <dockerhub-username>/fastapi-app

# ...

- name: Log in to Docker Hub
  uses: docker/login-action@v3
  with:
    username: ${{ secrets.DOCKERHUB_USERNAME }}
    password: ${{ secrets.DOCKERHUB_TOKEN }}
```

### AWS ECR

```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: us-east-1

- name: Login to Amazon ECR
  uses: aws-actions/amazon-ecr-login@v2

- name: Build and push
  uses: docker/build-push-action@v5
  with:
    push: true
    tags: <aws-account-id>.dkr.ecr.us-east-1.amazonaws.com/fastapi-app:latest
```

## Security Best Practices

1. **Use non-root user** (already configured in Dockerfile.production)
2. **Scan images for vulnerabilities**:
   ```bash
   docker scan ghcr.io/<username>/fastapi-http-websocket:latest
   ```
3. **Pin base image versions** (already using `python:3.13.0-slim-bullseye`)
4. **Keep images updated** - rebuild regularly with security patches
5. **Use secrets** - Never hardcode credentials in Dockerfile or code
6. **Enable image signing** (optional, for production):
   ```yaml
   - name: Sign image
     uses: docker/build-push-action@v5
     with:
       push: true
       tags: ${{ steps.meta.outputs.tags }}
       sign: true
   ```

## Monitoring

### GitHub Actions Badge

Add to README.md:

```markdown
![Docker Build](https://github.com/<username>/fastapi-http-websocket/actions/workflows/docker-build-push.yml/badge.svg)
```

### Image Metadata

View image labels:

```bash
docker inspect ghcr.io/<username>/fastapi-http-websocket:latest | jq '.[0].Config.Labels'
```

Labels include:
- `org.opencontainers.image.created` - Build timestamp
- `org.opencontainers.image.revision` - Git commit SHA
- `org.opencontainers.image.version` - Version tag

## Related Documentation

- [GitHub Container Registry Docs](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)
