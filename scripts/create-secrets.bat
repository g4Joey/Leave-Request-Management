@echo off
REM Create AWS Secrets Manager secrets for production deployment

echo 🔐 Creating AWS Secrets Manager secrets...

set AWS_REGION=us-east-1
set SECRET_PREFIX=leave-app

echo Creating Django secret key...
aws secretsmanager create-secret --name "%SECRET_PREFIX%/django-secret" --description "Django SECRET_KEY for Leave Management App" --secret-string "your-super-secret-production-key-here" --region %AWS_REGION%

echo Creating database URL secret...
aws secretsmanager create-secret --name "%SECRET_PREFIX%/database-url" --description "Database URL for Leave Management App" --secret-string "mysql://username:password@your-rds-endpoint.amazonaws.com:3306/leave_db" --region %AWS_REGION%

echo Creating seed users secret...
set SEED_USERS_JSON=[{"username":"jmankoe","first_name":"Ato","last_name":"Mankoe","email":"jmankoe@umbcapital.com","role":"manager","department":"IT","password":"Atokwamena"},{"username":"aakorfu","first_name":"Augustine","last_name":"Akorfu","email":"aakorfu@umbcapital.com","role":"staff","department":"IT","password":"AustineAkorfu"},{"username":"gsafo","first_name":"George","last_name":"Safo","email":"gsafo@umbcapital.com","role":"staff","department":"IT","password":"Georgesafo"}]
aws secretsmanager create-secret --name "%SECRET_PREFIX%/seed-users" --description "Seed users JSON for Leave Management App" --secret-string "%SEED_USERS_JSON%" --region %AWS_REGION%

echo Creating CEO credentials...
aws secretsmanager create-secret --name "%SECRET_PREFIX%/ceo-email" --description "CEO email for Leave Management App" --secret-string "ceo@your-domain.com" --region %AWS_REGION%
aws secretsmanager create-secret --name "%SECRET_PREFIX%/ceo-password" --description "CEO password for Leave Management App" --secret-string "YourSecurePassword123!" --region %AWS_REGION%

echo ✅ Secrets created successfully!
echo.
echo Next steps:
echo 1. Update the secret values with your actual credentials using AWS Console or CLI
echo 2. Update ecs-task-definition.json with your AWS account ID
echo 3. Deploy your ECS service
echo.
echo To update a secret value:
echo aws secretsmanager update-secret --secret-id "%SECRET_PREFIX%/database-url" --secret-string "your-actual-database-url" --region %AWS_REGION%
pause