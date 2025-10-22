# RDS Security Configuration for ECS Access

## Current RDS Details
- **Endpoint**: database-1.cxa60qms0gff.eu-north-1.rds.amazonaws.com
- **Region**: eu-north-1
- **Database**: database-1
- **Username**: g4Joey
- **Password**: RqDaBdWTyNXqMvGIH63E

## Required AWS Configuration Steps

### 1. RDS Security Group Configuration
Your RDS instance needs to allow connections from ECS tasks:

**In AWS Console → RDS → Databases → database-1 → Connectivity & security:**

1. Note the VPC ID and Security Groups
2. Click on the Security Group link
3. Add Inbound Rule:
   - **Type**: MySQL/Aurora (port 3306)
   - **Source**: Security Group of ECS tasks OR 0.0.0.0/0 for testing
   - **Description**: Allow ECS tasks to connect to RDS

### 2. VPC Configuration
Ensure both RDS and ECS are in the same VPC:

**Check RDS VPC:**
- AWS Console → RDS → Databases → database-1 → Connectivity & security → VPC

**Use same VPC for ECS:**
- When creating ECS service, use subnets from the same VPC

### 3. Subnet Groups
Ensure RDS is accessible from public subnets (if ECS tasks need internet access) or private subnets with NAT Gateway.

## CloudShell Commands to Check Configuration

### Check RDS Configuration
```bash
aws rds describe-db-instances --db-instance-identifier database-1 --region eu-north-1 --query 'DBInstances[0].{VpcId:DBSubnetGroup.VpcId,SecurityGroups:VpcSecurityGroups[*].VpcSecurityGroupId,PubliclyAccessible:PubliclyAccessible}'
```

### Check VPC and Subnets
```bash
# Get VPC ID from RDS
VPC_ID=$(aws rds describe-db-instances --db-instance-identifier database-1 --region eu-north-1 --query 'DBInstances[0].DBSubnetGroup.VpcId' --output text)

# Get subnets in the same VPC
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --region eu-north-1 --query 'Subnets[*].{SubnetId:SubnetId,AvailabilityZone:AvailabilityZone,MapPublicIpOnLaunch:MapPublicIpOnLaunch}'
```

### Get Security Group for ECS
```bash
# Get RDS security group
aws rds describe-db-instances --db-instance-identifier database-1 --region eu-north-1 --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' --output text
```

## If RDS is Not Accessible

### Option A: Modify RDS Security Group (Recommended)
1. Get ECS security group ID after creating service
2. Add inbound rule to RDS security group allowing port 3306 from ECS security group

### Option B: Temporarily Allow All Access (For Testing Only)
Add inbound rule to RDS security group:
- Type: MySQL/Aurora (3306)
- Source: 0.0.0.0/0
- **⚠️ Remember to remove this after testing**

## Verification Commands

After ECS deployment, test connectivity from ECS task:

```bash
# Get ECS task shell access
aws ecs execute-command --cluster leave-management-cluster --task [TASK_ARN] --container web --interactive --command "/bin/bash" --region eu-north-1

# Inside the container, test MySQL connection
mysql -h database-1.cxa60qms0gff.eu-north-1.rds.amazonaws.com -u g4Joey -p database-1
# Enter password: RqDaBdWTyNXqMvGIH63E
```

## Production Security Best Practices

1. **Use Secrets Manager** for database credentials
2. **Restrict RDS access** to only ECS security group
3. **Use private subnets** for RDS
4. **Enable VPC Flow Logs** for monitoring
5. **Regular security audits** of security groups