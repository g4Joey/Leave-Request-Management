# AWS CloudShell Deployment Guide
## Leave Management System Deployment

### Prerequisites
- AWS Account with access to CloudShell
- Docker image built locally (✅ Complete)
- Configuration files ready (✅ Complete)

---

## Step 1: Prepare Files Locally

You have already completed this:
- ✅ Docker image saved: `leave-app.tar` (ready for upload)
- ✅ Task definition: `ecs-task-definition-simple.json` (ready for upload)
- ✅ Deployment script: `scripts/cloudshell-deploy.sh` (ready for upload)

---

## Step 2: Access AWS CloudShell

1. **Login to AWS Console**
   - Go to https://console.aws.amazon.com
   - Login with your AWS account

2. **Open CloudShell**
   - Click the CloudShell icon (>_) in the top navigation bar
   - OR search for "CloudShell" in the services menu
   - Wait for initialization (30-60 seconds)

---

## Step 3: Upload Files to CloudShell

1. **Upload Files**
   - In CloudShell, click **Actions** → **Upload file**
   - Upload these files one by one:
     - `leave-app.tar` (Docker image - ~500MB, will take a few minutes)
     - `ecs-task-definition-simple.json`
     - `scripts/cloudshell-deploy.sh`

2. **Verify Upload**
   ```bash
   ls -la
   # Should show: leave-app.tar, ecs-task-definition-simple.json, cloudshell-deploy.sh
   ```

---

## Step 4: Run Deployment Script

1. **Make script executable**
   ```bash
   chmod +x cloudshell-deploy.sh
   ```

2. **Run the deployment script**
   ```bash
   ./cloudshell-deploy.sh
   ```

   This will:
   - Create ECR repository
   - Create ECS cluster
   - Create CloudWatch log group
   - Create IAM roles
   - Set up authentication

---

## Step 5: Upload Docker Image

After running the script, execute these commands in CloudShell:

1. **Load Docker image**
   ```bash
   docker load < leave-app.tar
   ```

2. **Tag the image**
   ```bash
   docker tag leave-request-app:latest 647132523767.dkr.ecr.eu-north-1.amazonaws.com/leave-request-app:latest
   ```

3. **Push to ECR**
   ```bash
   docker push 647132523767.dkr.ecr.eu-north-1.amazonaws.com/leave-request-app:latest
   ```

---

## Step 6: Register Task Definition

```bash
aws ecs register-task-definition --cli-input-json file://ecs-task-definition-simple.json --region eu-north-1
```

---

## Step 7: Get VPC Information

You need subnet and security group IDs for the service:

1. **Get Default VPC**
   ```bash
   aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --region eu-north-1
   ```

2. **Get Subnets**
   ```bash
   aws ec2 describe-subnets --filters "Name=default-for-az,Values=true" --region eu-north-1 --query 'Subnets[0].SubnetId' --output text
   ```

3. **Get Default Security Group**
   ```bash
   aws ec2 describe-security-groups --filters "Name=group-name,Values=default" --region eu-north-1 --query 'SecurityGroups[0].GroupId' --output text
   ```

---

## Step 8: Create ECS Service

Replace `subnet-xxxxx` and `sg-xxxxx` with values from Step 7:

```bash
aws ecs create-service \
    --cluster leave-management-cluster \
    --service-name leave-management-service \
    --task-definition leave-request-app-task \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxx],securityGroups=[sg-xxxxx],assignPublicIp=ENABLED}" \
    --region eu-north-1
```

---

## Step 9: Verify Deployment

1. **Check service status**
   ```bash
   aws ecs describe-services --cluster leave-management-cluster --services leave-management-service --region eu-north-1
   ```

2. **Check task status**
   ```bash
   aws ecs list-tasks --cluster leave-management-cluster --region eu-north-1
   ```

3. **Get public IP**
   ```bash
   # Get task ARN
   TASK_ARN=$(aws ecs list-tasks --cluster leave-management-cluster --region eu-north-1 --query 'taskArns[0]' --output text)
   
   # Get ENI ID
   ENI_ID=$(aws ecs describe-tasks --cluster leave-management-cluster --tasks $TASK_ARN --region eu-north-1 --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)
   
   # Get public IP
   aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --region eu-north-1 --query 'NetworkInterfaces[0].Association.PublicIp' --output text
   ```

---

## Step 10: Access Your Application

Once deployed:
- **Application URL**: `http://[PUBLIC_IP]:8000`
- **Admin Panel**: `http://[PUBLIC_IP]:8000/admin`
- **API**: `http://[PUBLIC_IP]:8000/api/`

**Default Users Created:**
- jmankoe (Manager - IT Department)
- aakorfu (Staff - IT Department)  
- gsafo (Staff - IT Department)
- CEO account with email: ceo@yourcompany.com

---

## Troubleshooting

### Check Logs
```bash
aws logs get-log-events --log-group-name /ecs/leave-request-app --log-stream-name ecs/web/[TASK_ID] --region eu-north-1
```

### Service Not Starting
- Check task definition registration
- Verify RDS security groups allow ECS access
- Check CloudWatch logs for errors

### Database Connection Issues
- Ensure RDS is in the same VPC as ECS
- Update RDS security groups to allow port 3306 from ECS security group
- Verify RDS endpoint and credentials

---

## Security Note
After deployment, consider:
1. Changing default passwords
2. Setting up proper SECRET_KEY
3. Configuring RDS security groups properly
4. Setting up Application Load Balancer for HTTPS