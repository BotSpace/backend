#!/bin/bash
# =============================================================================
# Flux GitOps Setup Script for BotMother
# =============================================================================
# Bu script serverda Flux o'rnatish va sozlash uchun ishlatiladi.
# Faqat bir marta ishga tushirish kerak.
#
# Talablar:
#   - kubectl o'rnatilgan va klasterga ulangan
#   - GitHub Personal Access Token (repo, admin:repo_hook scopelari bilan)
# =============================================================================

set -e

# Configuration
GITHUB_USER="${GITHUB_USER:-BotMather}"
GITHUB_REPO="${GITHUB_REPO:-backend}"
GITHUB_BRANCH="${GITHUB_BRANCH:-main}"
FLUX_PATH="${FLUX_PATH:-./flux/clusters/production}"
K8S_NAMESPACE="${K8S_NAMESPACE:-botmother}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-registry.jscorp.uz}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check prerequisites
check_prerequisites() {
    echo_info "Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        echo_error "kubectl is not installed. Please install it first."
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        echo_error "Cannot connect to Kubernetes cluster. Check your kubeconfig."
        exit 1
    fi
    
    echo_info "Prerequisites check passed!"
}

# Install Flux CLI
install_flux_cli() {
    if command -v flux &> /dev/null; then
        echo_info "Flux CLI already installed: $(flux --version)"
        return
    fi
    
    echo_info "Installing Flux CLI..."
    curl -s https://fluxcd.io/install.sh | sudo bash
    echo_info "Flux CLI installed: $(flux --version)"
}

# Check Flux prerequisites
check_flux_prereqs() {
    echo_info "Checking Flux prerequisites..."
    flux check --pre
}

# Bootstrap Flux
bootstrap_flux() {
    if [ -z "$GITHUB_TOKEN" ]; then
        echo_error "GITHUB_TOKEN environment variable is not set!"
        echo_info "Create a GitHub Personal Access Token with 'repo' and 'admin:repo_hook' scopes"
        echo_info "Then run: export GITHUB_TOKEN=<your-token>"
        exit 1
    fi
    
    echo_info "Bootstrapping Flux..."
    flux bootstrap github \
        --owner="$GITHUB_USER" \
        --repository="$GITHUB_REPO" \
        --branch="$GITHUB_BRANCH" \
        --path="$FLUX_PATH" \
        --personal \
        --components-extra=image-reflector-controller,image-automation-controller
    
    echo_info "Flux bootstrap completed!"
}

# Create namespace
create_namespace() {
    echo_info "Creating namespace $K8S_NAMESPACE..."
    kubectl create namespace "$K8S_NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
}

# Create Docker registry secret in flux-system namespace (for image scanning)
create_registry_secret_flux() {
    echo_info "Creating Docker registry secret in flux-system namespace..."
    
    if [ -z "$DOCKER_USERNAME" ] || [ -z "$DOCKER_PASSWORD" ]; then
        echo_warn "DOCKER_USERNAME or DOCKER_PASSWORD not set. Skipping registry secret for flux-system."
        echo_info "You can create it later with:"
        echo "  kubectl create secret docker-registry regcred -n flux-system \\"
        echo "    --docker-server=$DOCKER_REGISTRY \\"
        echo "    --docker-username=<username> \\"
        echo "    --docker-password=<password>"
        return
    fi
    
    kubectl create secret docker-registry regcred \
        --namespace=flux-system \
        --docker-server="$DOCKER_REGISTRY" \
        --docker-username="$DOCKER_USERNAME" \
        --docker-password="$DOCKER_PASSWORD" \
        --dry-run=client -o yaml | kubectl apply -f -
}

# Create Docker registry secret in app namespace
create_registry_secret_app() {
    echo_info "Creating Docker registry secret in $K8S_NAMESPACE namespace..."
    
    if [ -z "$DOCKER_USERNAME" ] || [ -z "$DOCKER_PASSWORD" ]; then
        echo_warn "DOCKER_USERNAME or DOCKER_PASSWORD not set. Skipping registry secret for app."
        return
    fi
    
    kubectl create secret docker-registry regcred \
        --namespace="$K8S_NAMESPACE" \
        --docker-server="$DOCKER_REGISTRY" \
        --docker-username="$DOCKER_USERNAME" \
        --docker-password="$DOCKER_PASSWORD" \
        --dry-run=client -o yaml | kubectl apply -f -
}

# Create application secrets
create_app_secrets() {
    echo_info "Creating application secrets..."
    
    # Check required secrets
    local missing_secrets=()
    [ -z "$DB_PASSWORD" ] && missing_secrets+=("DB_PASSWORD")
    [ -z "$DJANGO_SECRET_KEY" ] && missing_secrets+=("DJANGO_SECRET_KEY")
    [ -z "$MONGO_URL" ] && missing_secrets+=("MONGO_URL")
    
    if [ ${#missing_secrets[@]} -gt 0 ]; then
        echo_warn "Missing environment variables: ${missing_secrets[*]}"
        echo_info "Set them and run this script again, or create secrets manually:"
        echo "  kubectl create secret generic botmother-secrets -n $K8S_NAMESPACE \\"
        echo "    --from-literal=DB_PASSWORD=<value> \\"
        echo "    --from-literal=DJANGO_SECRET_KEY=<value> \\"
        echo "    --from-literal=MONGO_URL=<value> \\"
        echo "    ..."
        return
    fi
    
    kubectl create secret generic botmother-secrets \
        --namespace="$K8S_NAMESPACE" \
        --from-literal=POSTGRES_PASSWORD="${DB_PASSWORD}" \
        --from-literal=DB_PASSWORD="${DB_PASSWORD}" \
        --from-literal=DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY}" \
        --from-literal=MONGO_URL="${MONGO_URL}" \
        --from-literal=BOT_TOKEN="${BOT_TOKEN:-}" \
        --from-literal=TEST_BOT_TOKEN="${TEST_BOT_TOKEN:-}" \
        --from-literal=CLICK_SERVICE_ID="${CLICK_SERVICE_ID:-}" \
        --from-literal=CLICK_MERCHANT_ID="${CLICK_MERCHANT_ID:-}" \
        --from-literal=CLICK_SECRET_KEY="${CLICK_SECRET_KEY:-}" \
        --from-literal=DOCKER_USERNAME="${DOCKER_USERNAME:-}" \
        --from-literal=DOCKER_PASSWORD="${DOCKER_PASSWORD:-}" \
        --from-literal=DOCKER_REGISTRY="${DOCKER_REGISTRY}" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    echo_info "Application secrets created!"
}

# Create ConfigMap
create_configmap() {
    echo_info "Creating ConfigMap..."
    
    kubectl create configmap botmother-config \
        --namespace="$K8S_NAMESPACE" \
        --from-literal=DEBUG=False \
        --from-literal=DJANGO_SETTINGS_MODULE=config.settings.production \
        --from-literal=PROJECT_ENV=prod \
        --from-literal=PROTOCOL_HTTPS=true \
        --from-literal=SCRIPT=entrypoint-server.sh \
        --from-literal=PORT=8000 \
        --from-literal=DB_ENGINE=django_prometheus.db.backends.postgresql \
        --from-literal=DB_NAME=django \
        --from-literal=DB_USER=postgres \
        --from-literal=DB_HOST=postgres \
        --from-literal=DB_PORT=5432 \
        --from-literal=CACHE_BACKEND=django.core.cache.backends.redis.RedisCache \
        --from-literal=REDIS_URL=redis://redis:6379 \
        --from-literal=REDIS_HOST=redis \
        --from-literal=REDIS_PORT=6379 \
        --from-literal=CACHE_ENABLED=True \
        --from-literal=CACHE_TIMEOUT=120 \
        --from-literal=ALLOWED_HOSTS="127.0.0.1,web,botlarnionasi.jscorp.uz,api.botmother.uz" \
        --from-literal=CSRF_TRUSTED_ORIGINS="http://127.0.0.1:8081,https://botlarnionasi.jscorp.uz,https://api.botmother.uz" \
        --from-literal=API_URL=https://botlarnionasi.jscorp.uz \
        --from-literal=K8S_NAMESPACE="$K8S_NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    echo_info "ConfigMap created!"
}

# Apply image automation
apply_image_automation() {
    echo_info "Applying image automation configuration..."
    kubectl apply -f flux/apps/image-automation.yaml
    echo_info "Image automation applied!"
}

# Verify installation
verify_installation() {
    echo_info "Verifying Flux installation..."
    
    echo ""
    echo "=== Flux Components ==="
    flux check
    
    echo ""
    echo "=== Git Sources ==="
    flux get sources git
    
    echo ""
    echo "=== Kustomizations ==="
    flux get kustomizations
    
    echo ""
    echo "=== Image Repositories ==="
    flux get image repository 2>/dev/null || echo "No image repositories yet"
    
    echo ""
    echo "=== Image Policies ==="
    flux get image policy 2>/dev/null || echo "No image policies yet"
    
    echo ""
    echo_info "Verification complete!"
}

# Main
main() {
    echo "=============================================="
    echo "  BotMother Flux GitOps Setup"
    echo "=============================================="
    echo ""
    
    check_prerequisites
    install_flux_cli
    check_flux_prereqs
    
    echo ""
    echo_info "Ready to bootstrap Flux."
    echo_info "Make sure GITHUB_TOKEN is set!"
    read -p "Continue with bootstrap? (y/n) " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        bootstrap_flux
        create_namespace
        create_registry_secret_flux
        create_registry_secret_app
        create_app_secrets
        create_configmap
        
        echo ""
        echo_info "Waiting for Flux to reconcile..."
        sleep 10
        
        apply_image_automation
        verify_installation
        
        echo ""
        echo "=============================================="
        echo "  Setup Complete!"
        echo "=============================================="
        echo ""
        echo "Next steps:"
        echo "1. Push code changes to GitHub"
        echo "2. Flux will automatically deploy to Kubernetes"
        echo "3. Monitor with: flux get kustomizations --watch"
        echo ""
    else
        echo_info "Bootstrap cancelled."
    fi
}

# Run main
main "$@"
