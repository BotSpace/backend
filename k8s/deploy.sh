#!/bin/bash

# Kubernetes Deployment Script for BotMother Backend
# This script helps deploy the application to Kubernetes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster. Please check your kubectl configuration."
        exit 1
    fi
    
    log_info "Prerequisites check passed ✓"
}

create_secrets() {
    if [ ! -f "api-secrets.yaml" ]; then
        log_warn "api-secrets.yaml not found!"
        log_info "Creating from example template..."
        cp api-secrets.yaml.example api-secrets.yaml
        log_warn "Please edit api-secrets.yaml with your actual secret values before deploying!"
        read -p "Press enter to continue after editing secrets, or Ctrl+C to cancel..."
    fi
}

deploy_namespace() {
    log_info "Creating namespace..."
    kubectl apply -f namespace.yaml
}

deploy_secrets() {
    log_info "Deploying secrets..."
    kubectl apply -f api-secrets.yaml
}

deploy_configmap() {
    log_info "Deploying ConfigMap..."
    kubectl apply -f api-configmap.yaml
}

deploy_pvcs() {
    log_info "Creating Persistent Volume Claims..."
    kubectl apply -f pvcs.yaml
    
    log_info "Waiting for PVCs to be bound..."
    kubectl wait --for=condition=Bound pvc/logs-pvc -n botmother --timeout=60s || true
    kubectl wait --for=condition=Bound pvc/media-pvc -n botmother --timeout=60s || true
    kubectl wait --for=condition=Bound pvc/static-pvc -n botmother --timeout=60s || true
}

deploy_redis() {
    log_info "Deploying Redis DaemonSet..."
    kubectl apply -f redis-daemonset.yaml
    
    log_info "Waiting for Redis pods to be ready..."
    sleep 5
    kubectl rollout status daemonset/redis -n botmother --timeout=120s
    
    log_info "Redis DaemonSet deployed successfully ✓"
    kubectl get pods -n botmother -l app=redis -o wide
}

deploy_api() {
    log_info "Deploying API application..."
    kubectl apply -f api-deployment.yaml
    kubectl apply -f api-service.yaml
    
    log_info "Waiting for API deployment to be ready..."
    kubectl rollout status deployment/api -n botmother --timeout=180s
    
    log_info "API deployed successfully ✓"
}

verify_deployment() {
    log_info "Verifying deployment..."
    echo ""
    
    log_info "Pods status:"
    kubectl get pods -n botmother -o wide
    echo ""
    
    log_info "Services:"
    kubectl get svc -n botmother
    echo ""
    
    log_info "DaemonSet:"
    kubectl get daemonset -n botmother
    echo ""
    
    # Check if API can connect to Redis
    log_info "Checking Redis connectivity from API pod..."
    API_POD=$(kubectl get pod -n botmother -l app=api -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [ -n "$API_POD" ]; then
        NODE_IP=$(kubectl exec -n botmother $API_POD -- printenv NODE_IP 2>/dev/null || echo "")
        REDIS_URL=$(kubectl exec -n botmother $API_POD -- printenv REDIS_URL 2>/dev/null || echo "")
        
        log_info "API Pod: $API_POD"
        log_info "Node IP: $NODE_IP"
        log_info "Redis URL: $REDIS_URL"
        
        log_info "Testing Redis connection..."
        if kubectl exec -n botmother $API_POD -- sh -c "echo PING | nc -w 2 \$NODE_IP 6379" 2>/dev/null | grep -q "PONG"; then
            log_info "Redis connectivity test PASSED ✓"
        else
            log_warn "Redis connectivity test FAILED - Check logs for details"
        fi
    fi
}

show_logs() {
    log_info "Recent API logs:"
    kubectl logs -n botmother -l app=api --tail=20 || log_warn "Could not fetch logs"
}

# Main deployment flow
main() {
    log_info "Starting BotMother Kubernetes Deployment"
    echo ""
    
    check_prerequisites
    create_secrets
    
    echo ""
    read -p "Do you want to proceed with deployment? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_info "Deployment cancelled."
        exit 0
    fi
    
    deploy_namespace
    deploy_secrets
    deploy_configmap
    deploy_pvcs
    deploy_redis
    deploy_api
    
    echo ""
    log_info "Deployment completed!"
    echo ""
    
    verify_deployment
    
    echo ""
    show_logs
    
    echo ""
    log_info "Deployment Summary:"
    log_info "- Namespace: botmother"
    log_info "- Redis: Running as DaemonSet (one instance per node)"
    log_info "- API: Connected to node-local Redis instances"
    echo ""
    log_info "To check status: kubectl get all -n botmother"
    log_info "To view logs: kubectl logs -n botmother -l app=api -f"
}

# Script entry point
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Usage: $0 [options]"
    echo ""
    echo "Deploy BotMother backend to Kubernetes with node-local Redis."
    echo ""
    echo "Options:"
    echo "  --help, -h    Show this help message"
    echo ""
    echo "The script will:"
    echo "  1. Check prerequisites (kubectl, cluster access)"
    echo "  2. Create namespace"
    echo "  3. Deploy secrets and configmap"
    echo "  4. Create persistent volume claims"
    echo "  5. Deploy Redis as DaemonSet"
    echo "  6. Deploy API application"
    echo "  7. Verify deployment"
    exit 0
fi

main
