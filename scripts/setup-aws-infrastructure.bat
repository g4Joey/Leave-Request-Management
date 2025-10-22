@echo off
REM Complete AWS deployment setup script for Windows

echo 🚀 Setting up production Docker deployment on AWS...

REM Variables (edit these)
set AWS_REGION=eu-north-1
set CLUSTER_NAME=leave-request-cluster
set SERVICE_NAME=leave-request-service
set REPOSITORY_NAME=leave-request-app

echo 📋 Step 1: Create ECR repository...
aws ecr describe-repositories --repository-names %REPOSITORY_NAME% --region %AWS_REGION% >nul 2>&1 || aws ecr create-repository --repository-name %REPOSITORY_NAME% --region %AWS_REGION%

echo 📋 Step 2: Create CloudWatch Log Group...
aws logs create-log-group --log-group-name "/ecs/leave-request-app" --region %AWS_REGION% 2>nul || echo Log group already exists

echo 📋 Step 3: Create ECS cluster...
aws ecs describe-clusters --clusters %CLUSTER_NAME% --region %AWS_REGION% >nul 2>&1 || aws ecs create-cluster --cluster-name %CLUSTER_NAME% --capacity-providers FARGATE --region %AWS_REGION%

echo 📋 Step 4: Get Account ID...
for /f "tokens=*" %%i in ('aws sts get-caller-identity --query Account --output text') do set ACCOUNT_ID=%%i
echo Account ID: %ACCOUNT_ID%

echo 📋 Step 5: Update task definition with account ID...
powershell -Command "(Get-Content ecs-task-definition.json) -replace 'YOUR-ACCOUNT-ID', '%ACCOUNT_ID%' | Set-Content ecs-task-definition.json"

echo 📋 Step 6: Register task definition...
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json --region %AWS_REGION%

echo ✅ AWS infrastructure setup complete!
echo.
echo Next steps:
echo 1. Build and push your Docker image using scripts\build-and-push.bat
echo 2. Create an Application Load Balancer
echo 3. Create ECS service with the ALB
echo 4. Configure your domain and SSL certificate
pause