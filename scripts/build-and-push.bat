@echo off
REM Build and push Docker images to AWS ECR (Windows batch version)

set AWS_REGION=eu-north-1
set ECR_REGISTRY=647132523767.dkr.ecr.eu-north-1.amazonaws.com
set IMAGE_NAME=leave-request-app
set IMAGE_TAG=latest

echo 🐳 Building Docker image...
docker build -t %IMAGE_NAME%:%IMAGE_TAG% .

echo 🏷️ Tagging image for ECR...
docker tag %IMAGE_NAME%:%IMAGE_TAG% %ECR_REGISTRY%/%IMAGE_NAME%:%IMAGE_TAG%

echo 🔐 Logging into ECR...
for /f "tokens=*" %%i in ('aws ecr get-login-password --region %AWS_REGION%') do docker login --username AWS --password-stdin %ECR_REGISTRY% < echo %%i

echo 📤 Pushing image to ECR...
docker push %ECR_REGISTRY%/%IMAGE_NAME%:%IMAGE_TAG%

echo ✅ Image pushed successfully!
echo Image URI: %ECR_REGISTRY%/%IMAGE_NAME%:%IMAGE_TAG%
pause