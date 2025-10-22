@echo off
echo 🔐 AWS Secrets Manager Setup Guide
echo =================================
echo.
echo This script will help you create and update AWS secrets for your Leave Management app.
echo.

REM Check if AWS CLI is installed
aws --version >nul 2>&1
if errorlevel 1 (
    echo ❌ AWS CLI is not installed or not in PATH
    echo.
    echo Please install AWS CLI first:
    echo 1. Download from: https://aws.amazon.com/cli/
    echo 2. Or run: winget install Amazon.AWSCLI
    echo 3. Then run: aws configure
    echo.
    pause
    exit /b 1
)

echo ✅ AWS CLI is installed
echo.

REM Check if AWS is configured
aws sts get-caller-identity >nul 2>&1
if errorlevel 1 (
    echo ❌ AWS CLI is not configured
    echo.
    echo Please run: aws configure
    echo Enter your AWS Access Key ID, Secret Access Key, and region (us-east-1)
    echo.
    pause
    exit /b 1
)

echo ✅ AWS CLI is configured
echo.

set AWS_REGION=us-east-1

echo 📋 Creating/Updating AWS Secrets...
echo.

REM Django Secret Key
echo 1. Django Secret Key
set /p DJANGO_SECRET="Enter Django SECRET_KEY (50+ random characters): "
if not "%DJANGO_SECRET%"=="" (
    aws secretsmanager create-secret --name "leave-app/django-secret" --secret-string "%DJANGO_SECRET%" --region %AWS_REGION% 2>nul || aws secretsmanager update-secret --secret-id "leave-app/django-secret" --secret-string "%DJANGO_SECRET%" --region %AWS_REGION%
    echo ✅ Django secret updated
)

REM Database URL
echo.
echo 2. Database Connection
echo Example: mysql://admin:password@mydb.xyz123.us-east-1.rds.amazonaws.com:3306/leavedb
set /p DATABASE_URL="Enter your RDS Database URL: "
if not "%DATABASE_URL%"=="" (
    aws secretsmanager create-secret --name "leave-app/database-url" --secret-string "%DATABASE_URL%" --region %AWS_REGION% 2>nul || aws secretsmanager update-secret --secret-id "leave-app/database-url" --secret-string "%DATABASE_URL%" --region %AWS_REGION%
    echo ✅ Database URL updated
)

REM CEO Credentials
echo.
echo 3. CEO User Credentials
set /p CEO_EMAIL="Enter CEO email address: "
set /p CEO_PASSWORD="Enter CEO password: "
if not "%CEO_EMAIL%"=="" (
    aws secretsmanager create-secret --name "leave-app/ceo-email" --secret-string "%CEO_EMAIL%" --region %AWS_REGION% 2>nul || aws secretsmanager update-secret --secret-id "leave-app/ceo-email" --secret-string "%CEO_EMAIL%" --region %AWS_REGION%
    echo ✅ CEO email updated
)
if not "%CEO_PASSWORD%"=="" (
    aws secretsmanager create-secret --name "leave-app/ceo-password" --secret-string "%CEO_PASSWORD%" --region %AWS_REGION% 2>nul || aws secretsmanager update-secret --secret-id "leave-app/ceo-password" --secret-string "%CEO_PASSWORD%" --region %AWS_REGION%
    echo ✅ CEO password updated
)

REM Seed Users (from .env.production)
echo.
echo 4. Seed Users (using existing configuration from .env.production)
if exist ".env.production" (
    findstr "SEED_USERS=" .env.production > temp_seed.txt
    for /f "tokens=2 delims==" %%i in (temp_seed.txt) do (
        aws secretsmanager create-secret --name "leave-app/seed-users" --secret-string "%%i" --region %AWS_REGION% 2>nul || aws secretsmanager update-secret --secret-id "leave-app/seed-users" --secret-string "%%i" --region %AWS_REGION%
    )
    del temp_seed.txt 2>nul
    echo ✅ Seed users updated
) else (
    echo ❌ .env.production file not found
)

echo.
echo 🎉 All secrets have been created/updated!
echo.
echo Next steps:
echo 1. Update ecs-task-definition.json with your AWS Account ID
echo 2. Build and push your Docker image
echo 3. Deploy to ECS
echo.
echo To verify secrets were created:
echo aws secretsmanager list-secrets --region %AWS_REGION%
echo.
pause