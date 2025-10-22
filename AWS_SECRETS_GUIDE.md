# How to Update AWS Secrets Manager Secrets

## Prerequisites
You need AWS CLI installed and configured with your credentials.

### Install AWS CLI (if not already installed)
```cmd
# Download AWS CLI installer from: https://aws.amazon.com/cli/
# Or using winget:
winget install Amazon.AWSCLI
```

### Configure AWS CLI (one-time setup)
```cmd
aws configure
# Enter your:
# - AWS Access Key ID
# - AWS Secret Access Key  
# - Default region (e.g., us-east-1)
# - Output format (json)
```

## Method 1: AWS CLI Commands

### 1. Create the secrets first (one-time)
```cmd
# Django Secret Key
aws secretsmanager create-secret --name "leave-app/django-secret" --description "Django SECRET_KEY" --secret-string "your-super-secret-production-key-change-this-to-random-string" --region us-east-1

# Database URL (replace with your actual RDS endpoint)
aws secretsmanager create-secret --name "leave-app/database-url" --description "Database URL" --secret-string "mysql://your_db_user:your_db_password@your-rds-endpoint.amazonaws.com:3306/your_db_name" --region us-east-1

# Seed Users JSON
aws secretsmanager create-secret --name "leave-app/seed-users" --description "Seed users JSON" --secret-string "[{\"username\":\"jmankoe\",\"first_name\":\"Ato\",\"last_name\":\"Mankoe\",\"email\":\"jmankoe@umbcapital.com\",\"role\":\"manager\",\"department\":\"IT\",\"password\":\"Atokwamena\"},{\"username\":\"aakorfu\",\"first_name\":\"Augustine\",\"last_name\":\"Akorfu\",\"email\":\"aakorfu@umbcapital.com\",\"role\":\"staff\",\"department\":\"IT\",\"password\":\"AustineAkorfu\"},{\"username\":\"gsafo\",\"first_name\":\"George\",\"last_name\":\"Safo\",\"email\":\"gsafo@umbcapital.com\",\"role\":\"staff\",\"department\":\"IT\",\"password\":\"Georgesafo\"}]" --region us-east-1

# CEO Credentials
aws secretsmanager create-secret --name "leave-app/ceo-email" --description "CEO Email" --secret-string "ceo@yourcompany.com" --region us-east-1
aws secretsmanager create-secret --name "leave-app/ceo-password" --description "CEO Password" --secret-string "YourSecureCEOPassword123!" --region us-east-1
```

### 2. Update existing secrets with your actual values
```cmd
# Update Django Secret (generate a random 50-character string)
aws secretsmanager update-secret --secret-id "leave-app/django-secret" --secret-string "your-actual-50-character-random-secret-key-here" --region us-east-1

# Update Database URL with your RDS details
aws secretsmanager update-secret --secret-id "leave-app/database-url" --secret-string "mysql://admin:yourpassword@your-rds-instance.xyz123.us-east-1.rds.amazonaws.com:3306/leavedb" --region us-east-1

# Update CEO Email
aws secretsmanager update-secret --secret-id "leave-app/ceo-email" --secret-string "ceo@yourcompany.com" --region us-east-1

# Update CEO Password  
aws secretsmanager update-secret --secret-id "leave-app/ceo-password" --secret-string "YourActualCEOPassword123!" --region us-east-1
```

## Method 2: AWS Console (Web Interface)

### Step 1: Go to AWS Secrets Manager Console
1. Login to AWS Console
2. Search for "Secrets Manager" 
3. Select your region (us-east-1)

### Step 2: Create/Update Secrets
1. Click "Store a new secret"
2. Choose "Other type of secret"
3. Enter the secret name and value:

**Secrets to create:**

| Secret Name | Secret Value |
|-------------|--------------|
| `leave-app/django-secret` | `your-50-character-random-secret-key` |
| `leave-app/database-url` | `mysql://user:pass@your-rds-endpoint.amazonaws.com:3306/dbname` |
| `leave-app/seed-users` | `[{"username":"jmankoe",...}]` (the JSON from .env.production) |
| `leave-app/ceo-email` | `ceo@yourcompany.com` |
| `leave-app/ceo-password` | `YourSecureCEOPassword123!` |

### Step 3: Update Existing Secrets
1. Click on the secret name
2. Click "Retrieve secret value"  
3. Click "Edit"
4. Update the value
5. Click "Save"

## Method 3: Copy from .env.production file

You can copy the values directly from your `.env.production` file:

```cmd
# View your current .env.production values
type .env.production
```

Then use those values in the AWS CLI commands above.

## Verify Secrets Were Created
```cmd
# List all secrets
aws secretsmanager list-secrets --region us-east-1

# Get a specific secret value (to verify)
aws secretsmanager get-secret-value --secret-id "leave-app/django-secret" --region us-east-1
```

## Important Notes
- Replace `your-rds-endpoint.amazonaws.com` with your actual RDS endpoint
- Use strong, unique passwords for CEO and database
- The seed users JSON must be valid JSON (no line breaks in CLI)
- Keep your secret values secure - never commit them to git

After updating secrets, your ECS tasks will automatically pull the latest values when they restart.