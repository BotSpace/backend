#!/bin/bash
# Script to create registry credentials secret for pulling private images
# Usage: ./create-registry-secret.sh

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Docker Registry Credentials Setup ===${NC}"
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl is not installed${NC}"
    exit 1
fi

# Get registry details
echo "Enter Docker registry details:"
read -p "Registry server (e.g., registry.jscorp.uz): " REGISTRY_SERVER
read -p "Username: " REGISTRY_USERNAME
read -sp "Password: " REGISTRY_PASSWORD
echo ""
read -p "Email: " REGISTRY_EMAIL

NAMESPACE=${NAMESPACE:-botmother}
SECRET_NAME=${SECRET_NAME:-registry-credentials}

echo ""
echo -e "${YELLOW}Creating secret in namespace: $NAMESPACE${NC}"

# Create the secret
kubectl create secret docker-registry $SECRET_NAME \
  --namespace=$NAMESPACE \
  --docker-server=$REGISTRY_SERVER \
  --docker-username=$REGISTRY_USERNAME \
  --docker-password=$REGISTRY_PASSWORD \
  --docker-email=$REGISTRY_EMAIL \
  --dry-run=client -o yaml | kubectl apply -f -

echo -e "${GREEN}Secret '$SECRET_NAME' created successfully!${NC}"
echo ""
echo "To use this secret in your deployments, add the following to your deployment spec:"
echo ""
echo "  imagePullSecrets:"
echo "  - name: $SECRET_NAME"
echo ""
echo -e "${YELLOW}Example patch file for deployment:${NC}"
cat << EOF
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: botmother-web
spec:
  template:
    spec:
      imagePullSecrets:
      - name: $SECRET_NAME
EOF
