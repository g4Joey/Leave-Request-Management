#!/bin/bash
# AWS CloudShell Deployment Script for Leave Management System
# Run this script in AWS CloudShell

set -e  # Exit on error

echo "🚀 Starting AWS CloudShell Deployment"
echo "======================================"

# Variables
REGION="eu-north-1"
ACCOUNT_ID="647132523767"
ECR_REPOSITORY="leave-request-app"
ECS_CLUSTER="leave-management-cluster"
ECS_SERVICE="leave-management-service"
TASK_DEFINITION="leave-management-task"

echo "📋 Configuration:"
echo "   Region: $REGION"
echo "   Account ID: $ACCOUNT_ID"
echo "   ECR Repository: $ECR_REPOSITORY"
echo ""

# Step 1: Create ECR Repository
echo "🏗️  Step 1: Creating ECR Repository..."
aws ecr create-repository \
    --repository-name $ECR_REPOSITORY \
    --region $REGION \
    --image-scanning-configuration scanOnPush=true \
    || echo "   Repository might already exist, continuing..."

# Step 2: Get ECR login token and authenticate Docker
echo "🔐 Step 2: Authenticating with ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Step 3: Tag and push Docker image (you'll need to build this first)
echo "🐳 Step 3: Docker operations..."
echo "   Note: You need to build your Docker image locally first, then save it as a tar file"
echo "   Run locally: docker save leave-request-app:latest > leave-app.tar"
echo "   Then upload leave-app.tar to CloudShell using the Actions -> Upload file menu"
echo ""
echo "   After uploading, run these commands in CloudShell:"
echo "   docker load < leave-app.tar"
echo "   docker tag leave-request-app:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPOSITORY:latest"
echo "   docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPOSITORY:latest"
echo ""

# Step 4: Create ECS Cluster
echo "🎯 Step 4: Creating ECS Cluster..."
aws ecs create-cluster \
    --cluster-name $ECS_CLUSTER \
    --capacity-providers FARGATE \
    --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 \
    --region $REGION \
    || echo "   Cluster might already exist, continuing..."

# Step 5: Create CloudWatch Log Group
echo "📊 Step 5: Creating CloudWatch Log Group..."
aws logs create-log-group \
    --log-group-name /ecs/leave-management \
    --region $REGION \
    || echo "   Log group might already exist, continuing..."

# Step 6: Create IAM Role for ECS Task (if not exists)
echo "👤 Step 6: Creating ECS Task Execution Role..."
ROLE_NAME="ecsTaskExecutionRole"

# Check if role exists
if ! aws iam get-role --role-name $ROLE_NAME >/dev/null 2>&1; then
    # Create the role
    cat > trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file://trust-policy.json

    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

    echo "   Created ECS Task Execution Role"
else
    echo "   ECS Task Execution Role already exists"
fi

# Step 7: Register ECS Task Definition
echo "📝 Step 7: Registering ECS Task Definition..."
echo "   You need to upload your ecs-task-definition-simple.json file to CloudShell"
echo "   Then run: aws ecs register-task-definition --cli-input-json file://ecs-task-definition-simple.json --region $REGION"
echo ""

# Step 8: Create ECS Service
echo "🚀 Step 8: Instructions for creating ECS Service..."
echo "   After task definition is registered, create the service with:"
echo ""
cat << EOF
aws ecs create-service \\
    --cluster $ECS_CLUSTER \\
    --service-name $ECS_SERVICE \\
    --task-definition $TASK_DEFINITION \\
    --desired-count 1 \\
    --launch-type FARGATE \\
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxxxxx],securityGroups=[sg-xxxxxxxx],assignPublicIp=ENABLED}" \\
    --region $REGION
EOF
echo ""
echo "   Note: You'll need to replace subnet-xxxxxxxx and sg-xxxxxxxx with actual values from your VPC"

echo ""
echo "✅ Deployment script preparation complete!"
echo "📚 Next steps:"
echo "   1. Save your Docker image locally: docker save leave-request-app:latest > leave-app.tar"
echo "   2. Upload files to CloudShell: leave-app.tar, ecs-task-definition-simple.json"
echo "   3. Run this script in CloudShell"
echo "   4. Follow the manual steps for Docker operations and service creation"