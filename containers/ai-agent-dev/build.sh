#!/bin/bash
# Build script for AI Agent Development Container
# Supports both full and light variants

set -e

VERSION="${VERSION:-1.0.0}"
REGISTRY="${REGISTRY:-ghcr.io/kivo360}"
PUSH="${PUSH:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[BUILD]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Parse arguments
VARIANT="full"
while [[ $# -gt 0 ]]; do
    case $1 in
        --light)
            VARIANT="light"
            shift
            ;;
        --full)
            VARIANT="full"
            shift
            ;;
        --push)
            PUSH="true"
            shift
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --full          Build full variant (default)"
            echo "  --light         Build light variant"
            echo "  --push          Push to registry after build"
            echo "  --registry URL  Container registry (default: ghcr.io/kivo360)"
            echo "  --version VER   Image version tag (default: 1.0.0)"
            echo "  --help          Show this help"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Determine image name and dockerfile
if [ "$VARIANT" = "light" ]; then
    DOCKERFILE="Dockerfile.light"
    IMAGE_NAME="ai-agent-dev-light"
else
    DOCKERFILE="Dockerfile"
    IMAGE_NAME="ai-agent-dev"
fi

# Full image name with registry
FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${VERSION}"
LATEST_IMAGE="${REGISTRY}/${IMAGE_NAME}:latest"

log "Building ${VARIANT} variant..."
log "Image: ${FULL_IMAGE}"
log "Dockerfile: ${DOCKERFILE}"

# Check if dockerfile exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -f "$SCRIPT_DIR/$DOCKERFILE" ]; then
    error "Dockerfile not found: $SCRIPT_DIR/$DOCKERFILE"
fi

# Build for AMD64 (required for Daytona)
log "Building for linux/amd64..."
docker build \
    --platform=linux/amd64 \
    -t "${FULL_IMAGE}" \
    -t "${LATEST_IMAGE}" \
    -f "$SCRIPT_DIR/${DOCKERFILE}" \
    "$SCRIPT_DIR"

log "Build complete!"

# Show image size
IMAGE_SIZE=$(docker images "${FULL_IMAGE}" --format "{{.Size}}")
log "Image size: ${IMAGE_SIZE}"

# Push if requested
if [ "$PUSH" = "true" ]; then
    log "Pushing to ${REGISTRY}..."
    docker push "${FULL_IMAGE}"
    docker push "${LATEST_IMAGE}"
    log "Push complete!"
fi

# Print Daytona commands
echo ""
log "Next steps for Daytona:"
echo ""
echo "  # Push to Daytona as snapshot (full version)"
echo "  daytona snapshot push ${FULL_IMAGE} --name ${IMAGE_NAME} --cpu 4 --memory 8 --disk 20"
echo ""
echo "  # Or for light variant"
echo "  daytona snapshot push ${FULL_IMAGE} --name ${IMAGE_NAME} --cpu 2 --memory 4 --disk 10"
echo ""

# Print verification commands
echo "  # Verify the image"
echo "  docker run --rm ${FULL_IMAGE} bash -c 'rg --version && gh --version && python --version'"
