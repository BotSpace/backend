#!/bin/bash
# Pre-deployment validation script
# Checks if all prerequisites are met before deploying to Kubernetes

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Kubernetes Deployment Validator${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

print_header

echo "Checking prerequisites..."
echo ""

# Check kubectl
echo "1. Checking kubectl..."
if command -v kubectl &> /dev/null; then
    kubectl_version=$(kubectl version --client --short 2>/dev/null | grep -oP 'v\d+\.\d+\.\d+' || echo "unknown")
    check_pass "kubectl is installed (version: $kubectl_version)"
else
    check_fail "kubectl is not installed"
fi

# Check cluster connectivity
echo "2. Checking Kubernetes cluster connectivity..."
if kubectl cluster-info &> /dev/null; then
    check_pass "Connected to Kubernetes cluster"
    
    # Get cluster info
    cluster_info=$(kubectl cluster-info | head -1)
    echo "   └─ $cluster_info"
else
    check_fail "Cannot connect to Kubernetes cluster"
    echo "   └─ Run: kubectl config view"
fi

# Check namespace
echo "3. Checking namespace..."
if kubectl get namespace botmother &> /dev/null; then
    check_warn "Namespace 'botmother' already exists (deployment may update existing resources)"
else
    check_pass "Namespace 'botmother' does not exist (will be created)"
fi

# Check storage classes
echo "4. Checking storage classes..."
if kubectl get storageclass &> /dev/null; then
    sc_count=$(kubectl get storageclass --no-headers 2>/dev/null | wc -l)
    if [ "$sc_count" -gt 0 ]; then
        check_pass "Storage classes available: $sc_count"
        
        # Check if 'standard' exists
        if kubectl get storageclass standard &> /dev/null; then
            check_pass "Storage class 'standard' exists"
        else
            check_warn "Storage class 'standard' not found - you'll need to update k8s/base/pvc.yaml"
            echo "   Available storage classes:"
            kubectl get storageclass --no-headers | awk '{print "   - " $1}'
        fi
    else
        check_fail "No storage classes found"
    fi
else
    check_fail "Cannot check storage classes"
fi

# Check kustomize
echo "5. Checking kustomize..."
if kubectl kustomize --help &> /dev/null; then
    check_pass "kustomize is available (built into kubectl)"
else
    check_fail "kustomize is not available"
fi

# Validate kustomization files
echo "6. Validating kustomization files..."
if kubectl kustomize k8s/base > /dev/null 2>&1; then
    check_pass "Base kustomization is valid"
else
    check_fail "Base kustomization has errors"
fi

if kubectl kustomize k8s/overlays/production > /dev/null 2>&1; then
    check_pass "Production overlay is valid"
else
    check_fail "Production overlay has errors"
fi

# Check configuration placeholders
echo "7. Checking configuration..."

# Check if placeholders are still in configmap-patch
if grep -q "REPLACE_WITH_POSTGRES_HOST" k8s/overlays/production/configmap-patch.yaml 2>/dev/null; then
    check_fail "PostgreSQL host placeholder not replaced in configmap-patch.yaml"
else
    check_pass "PostgreSQL host is configured"
fi

if grep -q "REPLACE_WITH_REDIS_HOST" k8s/overlays/production/configmap-patch.yaml 2>/dev/null; then
    check_fail "Redis host placeholder not replaced in configmap-patch.yaml"
else
    check_pass "Redis host is configured"
fi

# Check secret placeholders
if grep -q "REPLACE_ME_OR_DEPLOYMENT_WILL_FAIL" k8s/base/secret.yaml 2>/dev/null; then
    check_warn "Secret file still contains placeholders - create secrets using kubectl"
    echo "   └─ Run: ./k8s/create-registry-secret.sh"
else
    check_pass "Secret placeholders have been replaced"
fi

# Check external services connectivity
echo "8. Checking external services (if configured)..."

# Extract hosts from configmap-patch if they exist
PG_HOST=$(grep "DB_HOST:" k8s/overlays/production/configmap-patch.yaml 2>/dev/null | grep -v "REPLACE" | awk -F'"' '{print $2}' | head -1)
REDIS_HOST=$(grep "REDIS_HOST:" k8s/overlays/production/configmap-patch.yaml 2>/dev/null | grep -v "REPLACE" | awk -F'"' '{print $2}' | head -1)

if [ -n "$PG_HOST" ] && [ "$PG_HOST" != "REPLACE_WITH_POSTGRES_HOST_IP_OR_DOMAIN" ]; then
    echo "   Testing PostgreSQL connectivity to $PG_HOST:5432..."
    if nc -zv -w 2 "$PG_HOST" 5432 &> /dev/null; then
        check_pass "PostgreSQL is reachable at $PG_HOST:5432"
    else
        check_warn "Cannot connect to PostgreSQL at $PG_HOST:5432 (may need to test from cluster)"
    fi
else
    check_warn "PostgreSQL host not configured yet"
fi

if [ -n "$REDIS_HOST" ] && [ "$REDIS_HOST" != "REPLACE_WITH_REDIS_HOST_IP_OR_DOMAIN" ]; then
    echo "   Testing Redis connectivity to $REDIS_HOST:6379..."
    if nc -zv -w 2 "$REDIS_HOST" 6379 &> /dev/null; then
        check_pass "Redis is reachable at $REDIS_HOST:6379"
    else
        check_warn "Cannot connect to Redis at $REDIS_HOST:6379 (may need to test from cluster)"
    fi
else
    check_warn "Redis host not configured yet"
fi

# Check if image pull secret is needed
echo "9. Checking image pull configuration..."
if grep -q "imagePullSecrets" k8s/base/deployment-web.yaml 2>/dev/null; then
    if kubectl get secret registry-credentials -n botmother &> /dev/null; then
        check_pass "Image pull secret 'registry-credentials' exists"
    else
        check_warn "Image pull secret configured but not found - run ./k8s/create-registry-secret.sh"
    fi
else
    check_pass "Using public registry (no pull secret needed)"
fi

# Summary
echo ""
echo "========================================="
echo "Validation Summary:"
echo "========================================="
echo -e "Passed:   ${GREEN}$PASSED${NC}"
echo -e "Failed:   ${RED}$FAILED${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ "$FAILED" -eq 0 ]; then
    if [ "$WARNINGS" -eq 0 ]; then
        echo -e "${GREEN}✓ All checks passed! Ready to deploy.${NC}"
        echo ""
        echo "Deploy with:"
        echo "  kubectl apply -k k8s/overlays/production"
        exit 0
    else
        echo -e "${YELLOW}⚠ Some warnings found. Review them before deploying.${NC}"
        echo ""
        echo "If warnings are acceptable, deploy with:"
        echo "  kubectl apply -k k8s/overlays/production"
        exit 0
    fi
else
    echo -e "${RED}✗ Validation failed. Fix the errors before deploying.${NC}"
    echo ""
    echo "Common fixes:"
    echo "1. Install kubectl: https://kubernetes.io/docs/tasks/tools/"
    echo "2. Configure cluster access: kubectl config view"
    echo "3. Update configuration: vim k8s/overlays/production/configmap-patch.yaml"
    echo "4. Create secrets: kubectl create secret generic ..."
    exit 1
fi
