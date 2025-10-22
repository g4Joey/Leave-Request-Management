#!/bin/bash
# Build and push Docker images to AWS ECR

set -e

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
ECR_REGISTRY=${ECR_REGISTRY:-your-account-id.dkr.ecr.us-east-1.amazonaws.com}
IMAGE_NAME=${IMAGE_NAME:-leave-request-app}
IMAGE_TAG=${IMAGE_TAG:-latest}

echo "🐳 Building Docker image..."
docker build -t $IMAGE_NAME:$IMAGE_TAG .

echo "🏷️ Tagging image for ECR..."
docker tag $IMAGE_NAME:$IMAGE_TAG $ECR_REGISTRY/$IMAGE_NAME:$IMAGE_TAG

echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

echo "📤 Pushing image to ECR..."
docker push $ECR_REGISTRY/$IMAGE_NAME:$IMAGE_TAG

echo "✅ Image pushed successfully!"
echo "Image URI: $ECR_REGISTRY/$IMAGE_NAME:$IMAGE_TAG"