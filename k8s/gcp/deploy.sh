#!/bin/bash

# GCP GKE Deployment Script for AI Assistant
# Prerequisites:
# - gcloud CLI configured
# - kubectl installed
# - Docker images pushed to GCR
# - GKE cluster created

set -e

echo "🚀 Deploying AI Assistant to GCP GKE"
echo "====================================="

# Variables - Update these or set them externally
if [ -z "${PROJECT_ID:-}" ]; then
  echo "❌ PROJECT_ID is required. Set the GCP project ID using the PROJECT_ID environment variable."
  exit 1
fi
CLUSTER_NAME="${GKE_CLUSTER_NAME:-ai-assistant-cluster}"
REGION="${GCP_REGION:-us-central1}"
GCR_REGISTRY="gcr.io/${PROJECT_ID}"

# Get cluster credentials
gcloud container clusters get-credentials ${CLUSTER_NAME} --region ${REGION} --project ${PROJECT_ID}

# Apply configurations
kubectl apply -f ../namespace.yaml
kubectl apply -f ../configmap.yaml
kubectl apply -f ../secret.yaml

# Update images in deployments
sed "s|your-registry/ai-assistant:latest|${GCR_REGISTRY}/ai-assistant:latest|g" ../ai-assistant.yaml | kubectl apply -f -
sed "s|your-registry/ecommerce-frontend:latest|${GCR_REGISTRY}/ecommerce-frontend:latest|g" ../frontend.yaml | kubectl apply -f -

# Apply other resources
kubectl apply -f ../zookeeper.yaml
kubectl apply -f ../kafka.yaml
kubectl apply -f ../pvc.yaml
kubectl apply -f ingress.yaml

# Create static IP (if not exists)
echo "Creating static IP address..."
gcloud compute addresses create ai-assistant-ip --region=${REGION} --project=${PROJECT_ID} 2>/dev/null || true

echo "⏳ Waiting for deployments..."
kubectl wait --for=condition=available --timeout=300s deployment/zookeeper -n ai-assistant
kubectl wait --for=condition=available --timeout=300s deployment/kafka -n ai-assistant
kubectl wait --for=condition=available --timeout=300s deployment/ai-assistant -n ai-assistant
kubectl wait --for=condition=available --timeout=300s deployment/ecommerce-frontend -n ai-assistant

echo "✅ Deployment complete!"
EXTERNAL_IP=$(gcloud compute addresses describe ai-assistant-ip --region=${REGION} --project=${PROJECT_ID} --format='value(address)')
echo "🌐 Access at: http://${EXTERNAL_IP}"