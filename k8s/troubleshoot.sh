#!/bin/bash

# Troubleshooting script for Kubernetes deployment
# This script helps diagnose issues with the node-local Redis setup

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

NAMESPACE="botmother"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo ""
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Check if namespace exists
check_namespace() {
    log_section "Checking Namespace"
    if kubectl get namespace $NAMESPACE &> /dev/null; then
        log_info "Namespace '$NAMESPACE' exists ✓"
    else
        log_error "Namespace '$NAMESPACE' does not exist!"
        echo "Create it with: kubectl apply -f namespace.yaml"
        exit 1
    fi
}

# Check Redis DaemonSet
check_redis() {
    log_section "Checking Redis DaemonSet"
    
    if ! kubectl get daemonset redis -n $NAMESPACE &> /dev/null; then
        log_error "Redis DaemonSet not found!"
        return 1
    fi
    
    echo "DaemonSet status:"
    kubectl get daemonset redis -n $NAMESPACE
    
    echo ""
    echo "Redis pods on each node:"
    kubectl get pods -n $NAMESPACE -l app=redis -o wide
    
    # Check if Redis pods are running
    REDIS_READY=$(kubectl get pods -n $NAMESPACE -l app=redis -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}' | wc -w)
    REDIS_TOTAL=$(kubectl get pods -n $NAMESPACE -l app=redis -o jsonpath='{.items[*].metadata.name}' | wc -w)
    
    echo ""
    if [ "$REDIS_READY" -eq "$REDIS_TOTAL" ] && [ "$REDIS_TOTAL" -gt 0 ]; then
        log_info "All Redis pods are running: $REDIS_READY/$REDIS_TOTAL ✓"
    else
        log_warn "Not all Redis pods are running: $REDIS_READY/$REDIS_TOTAL"
    fi
}

# Check API Deployment
check_api() {
    log_section "Checking API Deployment"
    
    if ! kubectl get deployment api -n $NAMESPACE &> /dev/null; then
        log_error "API Deployment not found!"
        return 1
    fi
    
    echo "Deployment status:"
    kubectl get deployment api -n $NAMESPACE
    
    echo ""
    echo "API pods:"
    kubectl get pods -n $NAMESPACE -l app=api -o wide
    
    # Check if API pods are running
    API_READY=$(kubectl get pods -n $NAMESPACE -l app=api -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}' | wc -w)
    API_TOTAL=$(kubectl get pods -n $NAMESPACE -l app=api -o jsonpath='{.items[*].metadata.name}' | wc -w)
    
    echo ""
    if [ "$API_READY" -eq "$API_TOTAL" ] && [ "$API_TOTAL" -gt 0 ]; then
        log_info "All API pods are running: $API_READY/$API_TOTAL ✓"
    else
        log_warn "Not all API pods are running: $API_READY/$API_TOTAL"
    fi
}

# Check Redis connectivity from API
check_connectivity() {
    log_section "Checking Redis Connectivity"
    
    API_PODS=$(kubectl get pods -n $NAMESPACE -l app=api -o jsonpath='{.items[*].metadata.name}')
    
    if [ -z "$API_PODS" ]; then
        log_error "No API pods found!"
        return 1
    fi
    
    for POD in $API_PODS; do
        echo ""
        log_info "Testing pod: $POD"
        
        # Get environment variables
        NODE_IP=$(kubectl exec -n $NAMESPACE $POD -- printenv NODE_IP 2>/dev/null || echo "NOT_SET")
        REDIS_URL=$(kubectl exec -n $NAMESPACE $POD -- printenv REDIS_URL 2>/dev/null || echo "NOT_SET")
        
        echo "  NODE_IP: $NODE_IP"
        echo "  REDIS_URL: $REDIS_URL"
        
        # Get the node the pod is running on
        NODE_NAME=$(kubectl get pod $POD -n $NAMESPACE -o jsonpath='{.spec.nodeName}')
        echo "  Running on node: $NODE_NAME"
        
        # Test Redis connection
        echo -n "  Testing Redis connection... "
        if kubectl exec -n $NAMESPACE $POD -- sh -c "echo PING | nc -w 2 \$NODE_IP 6379 2>/dev/null" | grep -q "PONG" 2>/dev/null; then
            echo -e "${GREEN}SUCCESS ✓${NC}"
        else
            echo -e "${RED}FAILED ✗${NC}"
            log_warn "Could not connect to Redis at $NODE_IP:6379"
        fi
    done
}

# Check logs
check_logs() {
    log_section "Recent Logs"
    
    echo "API logs (last 20 lines):"
    kubectl logs -n $NAMESPACE -l app=api --tail=20 2>&1 || log_warn "Could not fetch API logs"
    
    echo ""
    echo "Redis logs (last 10 lines from first pod):"
    REDIS_POD=$(kubectl get pods -n $NAMESPACE -l app=redis -o jsonpath='{.items[0].metadata.name}')
    if [ -n "$REDIS_POD" ]; then
        kubectl logs -n $NAMESPACE $REDIS_POD --tail=10 2>&1 || log_warn "Could not fetch Redis logs"
    fi
}

# Check events
check_events() {
    log_section "Recent Events"
    kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -20
}

# Show summary
show_summary() {
    log_section "Summary"
    
    echo "All resources in namespace '$NAMESPACE':"
    kubectl get all -n $NAMESPACE
    
    echo ""
    echo "ConfigMaps:"
    kubectl get configmap -n $NAMESPACE
    
    echo ""
    echo "Secrets:"
    kubectl get secret -n $NAMESPACE
    
    echo ""
    echo "PersistentVolumeClaims:"
    kubectl get pvc -n $NAMESPACE
}

# Main function
main() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════╗"
    echo "║  Kubernetes Deployment Troubleshooting    ║"
    echo "║  Namespace: $NAMESPACE                    ║"
    echo "╚════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    check_namespace
    check_redis
    check_api
    check_connectivity
    check_logs
    check_events
    show_summary
    
    echo ""
    log_info "Troubleshooting complete!"
}

# Run main
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Usage: $0"
    echo ""
    echo "This script checks the health and connectivity of the Kubernetes deployment."
    echo "It verifies:"
    echo "  - Namespace existence"
    echo "  - Redis DaemonSet status"
    echo "  - API Deployment status"
    echo "  - Redis connectivity from API pods"
    echo "  - Recent logs and events"
    exit 0
fi

main
