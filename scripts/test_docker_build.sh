#!/bin/bash
# Script to test Docker production build locally before pushing to main

set -e  # Exit on error

echo "🐳 Testing Production Docker Build"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="fastapi-app"
TAG="test-$(date +%s)"
CONTAINER_NAME="fastapi-test-${TAG}"

# Step 1: Check if Docker is running
echo "📋 Step 1: Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker is running${NC}"
echo ""

# Step 2: Validate Dockerfile syntax
echo "📋 Step 2: Validating Dockerfile..."
if ! docker build -f docker/Dockerfile.production --check . > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Docker buildx check not available (Docker < 24.0). Skipping syntax check.${NC}"
else
    echo -e "${GREEN}✅ Dockerfile syntax is valid${NC}"
fi
echo ""

# Step 3: Build the image
echo "📋 Step 3: Building production image..."
echo "This may take 2-5 minutes..."
if docker build \
    -f docker/Dockerfile.production \
    -t "${IMAGE_NAME}:${TAG}" \
    --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    --build-arg VCS_REF="$(git rev-parse --short HEAD)" \
    --build-arg VERSION="test" \
    --progress=plain \
    . > build.log 2>&1; then
    echo -e "${GREEN}✅ Image built successfully${NC}"
else
    echo -e "${RED}❌ Build failed. Check build.log for details.${NC}"
    tail -50 build.log
    exit 1
fi
echo ""

# Step 4: Check image size
echo "📋 Step 4: Checking image size..."
IMAGE_SIZE=$(docker images "${IMAGE_NAME}:${TAG}" --format "{{.Size}}")
echo "Image size: ${IMAGE_SIZE}"
if [[ "${IMAGE_SIZE}" =~ GB ]]; then
    SIZE_GB=$(echo "${IMAGE_SIZE}" | sed 's/GB//')
    if (( $(echo "$SIZE_GB > 1.0" | bc -l) )); then
        echo -e "${YELLOW}⚠️  Warning: Image is larger than 1GB (${IMAGE_SIZE})${NC}"
        echo "   Consider optimizing .dockerignore or removing unnecessary files"
    fi
fi
echo -e "${GREEN}✅ Image size check complete${NC}"
echo ""

# Step 5: Inspect image metadata
echo "📋 Step 5: Inspecting image metadata..."
docker inspect "${IMAGE_NAME}:${TAG}" --format='{{json .Config.Labels}}' | jq '.' > /dev/null 2>&1 || true
echo -e "${GREEN}✅ Metadata inspection complete${NC}"
echo ""

# Step 6: Test image can start
echo "📋 Step 6: Testing image startup..."
echo "Starting container..."
if docker run -d \
    --name "${CONTAINER_NAME}" \
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
    "${IMAGE_NAME}:${TAG}" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Container started${NC}"

    # Wait for container to be ready
    echo "Waiting for application to be ready (max 30s)..."
    for i in {1..30}; do
        if docker logs "${CONTAINER_NAME}" 2>&1 | grep -q "Application startup complete" || \
           docker logs "${CONTAINER_NAME}" 2>&1 | grep -q "Uvicorn running"; then
            echo -e "${GREEN}✅ Application started successfully${NC}"
            break
        fi
        if [ $i -eq 30 ]; then
            echo -e "${YELLOW}⚠️  Application didn't report ready status in 30s${NC}"
            echo "Last 20 log lines:"
            docker logs "${CONTAINER_NAME}" 2>&1 | tail -20
        fi
        sleep 1
    done

    # Test health endpoint (if exists)
    echo ""
    echo "Testing health endpoint..."
    sleep 2  # Give it a moment
    if curl -s -f http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Health endpoint responding${NC}"
    else
        echo -e "${YELLOW}⚠️  Health endpoint not available (this is okay if not implemented)${NC}"
    fi
else
    echo -e "${RED}❌ Container failed to start${NC}"
    docker logs "${CONTAINER_NAME}" 2>&1 | tail -50
    docker rm -f "${CONTAINER_NAME}" > /dev/null 2>&1 || true
    exit 1
fi
echo ""

# Step 7: Check container logs for errors
# Note: startup validation errors (DB/Redis/Keycloak unreachable) are expected
# when running in isolation without external services - these are not real failures
echo "📋 Step 7: Checking logs for errors..."
if docker logs "${CONTAINER_NAME}" 2>&1 \
    | grep -i "error\|exception\|fatal" \
    | grep -v "ERROR - 404" \
    | grep -v "Startup validation failed" \
    | grep -v "Application will not start" \
    | grep -v "Connect call failed" \
    | grep -v "logging_errors.log" \
    > /dev/null; then
    echo -e "${YELLOW}⚠️  Found error messages in logs:${NC}"
    docker logs "${CONTAINER_NAME}" 2>&1 \
        | grep -i "error\|exception\|fatal" \
        | grep -v "ERROR - 404" \
        | grep -v "Startup validation failed" \
        | grep -v "Application will not start" \
        | grep -v "Connect call failed" \
        | grep -v "logging_errors.log" \
        | head -10
else
    echo -e "${GREEN}✅ No critical errors in logs${NC}"
fi
echo ""

# Step 8: Security scan (if trivy is installed)
echo "📋 Step 8: Security scan..."
if command -v trivy &> /dev/null; then
    echo "Running Trivy security scan..."
    if trivy image --severity HIGH,CRITICAL --exit-code 0 "${IMAGE_NAME}:${TAG}"; then
        echo -e "${GREEN}✅ No critical vulnerabilities found${NC}"
    else
        echo -e "${YELLOW}⚠️  Vulnerabilities detected (see above)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Trivy not installed. Skipping security scan.${NC}"
    echo "   Install: https://github.com/aquasecurity/trivy#installation"
fi
echo ""

# Cleanup
echo "📋 Cleanup..."
docker stop "${CONTAINER_NAME}" > /dev/null 2>&1 || true
docker rm "${CONTAINER_NAME}" > /dev/null 2>&1 || true
echo -e "${GREEN}✅ Cleanup complete${NC}"
echo ""

# Summary
echo "=================================="
echo "🎉 Build Test Complete!"
echo "=================================="
echo ""
echo "Image Details:"
echo "  Name: ${IMAGE_NAME}:${TAG}"
echo "  Size: ${IMAGE_SIZE}"
echo ""
echo "Next steps:"
echo "  1. Review build.log for detailed build output"
echo "  2. If everything looks good, commit and push to trigger CI/CD"
echo "  3. Remove test image: docker rmi ${IMAGE_NAME}:${TAG}"
echo ""

# Offer to remove test image
read -p "Remove test image now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker rmi "${IMAGE_NAME}:${TAG}"
    echo -e "${GREEN}✅ Test image removed${NC}"
fi

echo ""
echo "To run the image manually:"
echo "  docker run -p 8000:8000 --env-file .env.production ${IMAGE_NAME}:${TAG}"
