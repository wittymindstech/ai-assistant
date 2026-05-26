#!/bin/bash

# AWS EKS Deployment Script for AI Assistant
# Prerequisites:
# - AWS CLI configured
# - kubectl installed and configured for EKS
# - Docker images pushed to ECR
# - EKS cluster created

set -e

echo "🚀 Deploying AI Assistant to AWS EKS"
echo "===================================="

# Variables - Update these or set them externally
CLUSTER_NAME="${EKS_CLUSTER_NAME:-ai-assistant-cluster}"
REGION="${AWS_REGION:-us-east-1}"
if [ -z "${AWS_ACCOUNT_ID:-}" ]; then
  echo "❌ AWS_ACCOUNT_ID is required."
  exit 1
fi
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# Update ConfigMap with actual values if needed
kubectl apply -f ../namespace.yaml
kubectl apply -f ../configmap.yaml
kubectl apply -f ../secret.yaml

# Update images in deployments
sed "s|your-registry/ai-assistant:latest|${ECR_REGISTRY}/ai-assistant:latest|g" ../ai-assistant.yaml | kubectl apply -f -
sed "s|your-registry/ecommerce-frontend:latest|${ECR_REGISTRY}/ecommerce-frontend:latest|g" ../frontend.yaml | kubectl apply -f -

# Apply other resources
kubectl apply -f ../zookeeper.yaml
kubectl apply -f ../kafka.yaml
kubectl apply -f ../pvc.yaml
kubectl apply -f ingress.yaml

echo "⏳ Waiting for deployments..."
kubectl wait --for=condition=available --timeout=300s deployment/zookeeper -n ai-assistant
kubectl wait --for=condition=available --timeout=300s deployment/kafka -n ai-assistant
kubectl wait --for=condition=available --timeout=300s deployment/ai-assistant -n ai-assistant
kubectl wait --for=condition=available --timeout=300s deployment/ecommerce-frontend -n ai-assistant

echo "✅ Deployment complete!"
echo "🌐 Ingress URL: $(kubectl get ingress ai-assistant-ingress-aws -n ai-assistant -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')"