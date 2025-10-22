@echo off
echo 🚀 Leave Management App - AWS Deployment Script
echo ===============================================
echo.
echo Your configuration:
echo - AWS Account: 647132523767
echo - Region: eu-north-1
echo - RDS: database-1.cxa60qms0gff.eu-north-1.rds.amazonaws.com
echo.

REM Check if Docker is running
docker version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running or not installed
    echo Please start Docker Desktop and try again
    pause
    exit /b 1
)
echo ✅ Docker is running

REM Build Docker image
echo.
echo 📦 Building Docker image...
docker build -t leave-request-app:latest .
if errorlevel 1 (
    echo ❌ Docker build failed
    pause
    exit /b 1
)
echo ✅ Docker image built successfully

REM Test the image locally (optional)
echo.
echo 🧪 Testing Docker image locally...
echo Starting container on port 8001 for 10 seconds...
docker run --env-file .env.production -d -p 8001:8000 --name leave-test leave-request-app:latest
echo Waiting 10 seconds for startup...
timeout /t 10 /nobreak >nul
docker logs leave-test
docker stop leave-test >nul 2>&1
docker rm leave-test >nul 2>&1
echo ✅ Local test completed

echo.
echo 📋 Next Steps:
echo.
echo 1. Install AWS CLI and configure it:
echo    - Download: https://aws.amazon.com/cli/
echo    - Run: aws configure
echo    - Enter your AWS credentials and set region to eu-north-1
echo.
echo 2. Push to ECR:
echo    scripts\build-and-push.bat
echo.
echo 3. Setup AWS infrastructure:
echo    scripts\setup-aws-infrastructure.bat
echo.
echo 4. Create ECS service (manual step in AWS Console)
echo.
echo Your Docker image is ready! 
echo Files configured for account: 647132523767
echo.
pause