# Production Docker Deployment Guide

## Prerequisites
1. Docker Desktop installed and running
2. AWS CLI configured with proper permissions
3. Your RDS MySQL database created and accessible

## Quick Setup Commands

### 1. Start Docker Desktop
Make sure Docker Desktop is running on your machine.

### 2. Create Production Environment File
```cmd
copy .env.production.example .env.production
```
Edit `.env.production` with your actual RDS connection details:
- `DATABASE_URL=mysql://username:password@your-rds-endpoint.amazonaws.com:3306/dbname`
- `SECRET_KEY=your-production-secret-key`
- `ALLOWED_HOSTS=your-domain.com`
- `CEO_EMAIL` and `CEO_PASSWORD`

### 3. Build Docker Image
```cmd
docker build -t leave-request-app:latest .
```

### 4. Test Locally with Production Settings
```cmd
docker run --env-file .env.production -p 8000:8000 leave-request-app:latest
```

### 5. Create ECR Repository (one-time setup)
```cmd
aws ecr create-repository --repository-name leave-request-app --region us-east-1
```

### 6. Push to ECR
First, get your AWS account ID:
```cmd
aws sts get-caller-identity --query Account --output text
```

Then update `scripts/build-and-push.bat` with your account ID and run:
```cmd
scripts\build-and-push.bat
```

### 7. Deploy to ECS (Manual Steps)
1. Create ECS Cluster (Fargate)
2. Create CloudWatch Log Group: `/ecs/leave-request-app`
3. Update `ecs-task-definition.json` with your account ID
4. Register task definition:
```cmd
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json
```
5. Create ECS Service with ALB

## Production Checklist
- [ ] RDS MySQL database created and accessible
- [ ] ECR repository created
- [ ] Docker image built and pushed
- [ ] ECS cluster created
- [ ] Application Load Balancer configured
- [ ] Security groups allow traffic on port 80/443
- [ ] Route 53 DNS configured (optional)
- [ ] SSL certificate configured in ALB
- [ ] Environment variables configured in task definition

## Environment Variables Required
- `DATABASE_URL` or `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `CEO_EMAIL`, `CEO_PASSWORD`
- `AWS_STORAGE_BUCKET_NAME` (for S3 media storage)

## Troubleshooting
- If Docker build fails, ensure Docker Desktop is running
- If RDS connection fails, check security groups and VPC settings
- If migrations fail, ensure RDS allows connections from your ECS tasks
- Check CloudWatch logs for runtime errors

## Next Steps After Deployment
1. Run initial migration: Connect to ECS task and run `python manage.py migrate`
2. Create CEO user: Will be created automatically if `CEO_EMAIL` and `CEO_PASSWORD` are set
3. Set up S3 for media files (recommended for production)
4. Configure CloudFront for static file caching
5. Set up monitoring with CloudWatch and SNS alerts