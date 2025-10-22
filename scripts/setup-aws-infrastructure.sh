#!/bin/bash
# Complete AWS deployment setup script

set -e

echo "🚀 Setting up production Docker deployment on AWS..."

# Variables (edit these)
AWS_REGION="us-east-1"
CLUSTER_NAME="leave-request-cluster"
SERVICE_NAME="leave-request-service"
REPOSITORY_NAME="leave-request-app"

echo "📋 Step 1: Create ECR repository..."
aws ecr describe-repositories --repository-names $REPOSITORY_NAME --region $AWS_REGION 2>/dev/null || \
aws ecr create-repository --repository-name $REPOSITORY_NAME --region $AWS_REGION

echo "📋 Step 2: Create CloudWatch Log Group..."
aws logs describe-log-groups --log-group-name-prefix "/ecs/leave-request-app" --region $AWS_REGION --query 'logGroups[0].logGroupName' --output text 2>/dev/null | grep -q "/ecs/leave-request-app" || \
aws logs create-log-group --log-group-name "/ecs/leave-request-app" --region $AWS_REGION

echo "📋 Step 3: Create ECS cluster..."
aws ecs describe-clusters --clusters $CLUSTER_NAME --region $AWS_REGION --query 'clusters[0].clusterName' --output text 2>/dev/null | grep -q $CLUSTER_NAME || \
aws ecs create-cluster --cluster-name $CLUSTER_NAME --capacity-providers FARGATE --region $AWS_REGION

echo "📋 Step 4: Get Account ID..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account ID: $ACCOUNT_ID"

echo "📋 Step 5: Update task definition with account ID..."
sed -i "s/YOUR-ACCOUNT-ID/$ACCOUNT_ID/g" ecs-task-definition.json

echo "📋 Step 6: Register task definition..."
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json --region $AWS_REGION

echo "✅ AWS infrastructure setup complete!"
echo ""
echo "Next steps:"
echo "1. Build and push your Docker image using scripts/build-and-push.sh"
echo "2. Create an Application Load Balancer"
echo "3. Create ECS service with the ALB"
echo "4. Configure your domain and SSL certificate"