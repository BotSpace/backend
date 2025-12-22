#!/bin/bash
# Kubernetes Deployment Helper Script
# This script helps deploy the BotMother backend to Kubernetes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed. Please install kubectl first."
    exit 1
fi

# Check if cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
    exit 1
fi

print_info "Kubernetes cluster is accessible"

# Display menu
echo ""
echo "=========================================="
echo "  BotMother K8s Deployment Helper"
echo "=========================================="
echo ""
echo "1. Deploy to production (with kustomize)"
echo "2. Update deployment (rolling update)"
echo "3. Check deployment status"
echo "4. View logs"
echo "5. Run database migrations"
echo "6. Create superuser"
echo "7. Rollback deployment"
echo "8. Scale deployment"
echo "9. Delete deployment"
echo "0. Exit"
echo ""
read -p "Select an option: " option

case $option in
    1)
        print_info "Deploying to production..."
        print_warn "Please ensure you have updated the configuration files first!"
        read -p "Continue? (y/n): " confirm
        if [ "$confirm" = "y" ]; then
            kubectl apply -k k8s/overlays/production
            print_info "Deployment initiated. Use option 3 to check status."
        fi
        ;;
    2)
        print_info "Updating deployment..."
        read -p "Enter new image tag (e.g., v1.0.1): " tag
        read -p "Enter nginx image tag (or press enter for 'latest'): " nginx_tag
        nginx_tag=${nginx_tag:-latest}
        if [ -n "$tag" ]; then
            kubectl set image deployment/botmother-web web=registry.jscorp.uz/botmother:$tag -n botmother
            kubectl set image deployment/botmother-nginx nginx=jscorptech/nginx:$nginx_tag -n botmother
            print_info "Image updated. Rolling update in progress..."
            kubectl rollout status deployment/botmother-web -n botmother
        fi
        ;;
    3)
        print_info "Checking deployment status..."
        echo ""
        echo "=== Pods ==="
        kubectl get pods -n botmother
        echo ""
        echo "=== Services ==="
        kubectl get svc -n botmother
        echo ""
        echo "=== Deployments ==="
        kubectl get deployments -n botmother
        ;;
    4)
        print_info "Select component to view logs:"
        echo "1. Web"
        echo "2. Nginx"
        read -p "Select: " component
        case $component in
            1)
                kubectl logs -n botmother -l component=web --tail=100 -f
                ;;
            2)
                kubectl logs -n botmother -l component=nginx --tail=100 -f
                ;;
            *)
                print_error "Invalid option"
                ;;
        esac
        ;;
    5)
        print_info "Running database migrations..."
        kubectl exec -n botmother -it deployment/botmother-web -- python manage.py migrate
        print_info "Migrations completed"
        ;;
    6)
        print_info "Creating superuser..."
        kubectl exec -n botmother -it deployment/botmother-web -- python manage.py createsuperuser
        ;;
    7)
        print_info "Rolling back deployment..."
        kubectl rollout undo deployment/botmother-web -n botmother
        print_info "Rollback initiated"
        kubectl rollout status deployment/botmother-web -n botmother
        ;;
    8)
        print_info "Scaling deployment..."
        read -p "Enter number of replicas for web: " web_replicas
        read -p "Enter number of replicas for nginx: " nginx_replicas
        kubectl scale deployment botmother-web --replicas=$web_replicas -n botmother
        kubectl scale deployment botmother-nginx --replicas=$nginx_replicas -n botmother
        print_info "Scaling complete"
        ;;
    9)
        print_warn "This will DELETE all resources in the botmother namespace!"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            kubectl delete -k k8s/overlays/production
            print_info "Resources deleted"
        fi
        ;;
    0)
        print_info "Exiting..."
        exit 0
        ;;
    *)
        print_error "Invalid option"
        exit 1
        ;;
esac
