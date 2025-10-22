# AWS Console Setup Guide (No CLI Required)

Since AWS CLI isn't installed, you can set up everything through the AWS Console web interface.

## Step 1: Create AWS Secrets Manager Secrets (Web Console)

### 1. Go to AWS Secrets Manager Console
1. Login to your AWS Console
2. Search for "Secrets Manager" in the search bar
3. Click on "AWS Secrets Manager"
4. Make sure you're in the correct region (us-east-1)

### 2. Create Each Secret

Click "Store a new secret" and create these 5 secrets:

#### Secret 1: Django Secret Key
- **Secret type:** Other type of secret
- **Key:** (leave blank, just put value in plaintext)
- **Plaintext value:** `your-super-secret-django-key-50-characters-long-change-this`
- **Secret name:** `leave-app/django-secret`
- **Description:** Django SECRET_KEY for Leave Management App
- Click "Next" → "Next" → "Store"

#### Secret 2: Database URL
- **Secret type:** Other type of secret  
- **Plaintext value:** `mysql://your_db_user:your_db_password@your-rds-endpoint.amazonaws.com:3306/your_db_name`
- **Secret name:** `leave-app/database-url`
- **Description:** Database URL for Leave Management App
- **Replace with your actual RDS details:**
  - `your_db_user` = your RDS master username
  - `your_db_password` = your RDS master password
  - `your-rds-endpoint.amazonaws.com` = your RDS endpoint URL
  - `your_db_name` = your database name

#### Secret 3: Seed Users JSON
- **Secret type:** Other type of secret
- **Plaintext value:** 
```json
[{"username":"jmankoe","first_name":"Ato","last_name":"Mankoe","email":"jmankoe@umbcapital.com","role":"manager","department":"IT","password":"Atokwamena"},{"username":"aakorfu","first_name":"Augustine","last_name":"Akorfu","email":"aakorfu@umbcapital.com","role":"staff","department":"IT","password":"AustineAkorfu"},{"username":"gsafo","first_name":"George","last_name":"Safo","email":"gsafo@umbcapital.com","role":"staff","department":"IT","password":"Georgesafo"}]
```
- **Secret name:** `leave-app/seed-users`
- **Description:** Seed users JSON for Leave Management App

#### Secret 4: CEO Email
- **Secret type:** Other type of secret
- **Plaintext value:** `ceo@yourcompany.com` (replace with actual CEO email)
- **Secret name:** `leave-app/ceo-email`
- **Description:** CEO email for Leave Management App

#### Secret 5: CEO Password
- **Secret type:** Other type of secret
- **Plaintext value:** `YourSecureCEOPassword123!` (replace with secure password)
- **Secret name:** `leave-app/ceo-password`
- **Description:** CEO password for Leave Management App

## Step 2: Get Your AWS Account ID

### Method 1: From AWS Console
1. Click on your username in top-right corner
2. Your 12-digit Account ID is shown in the dropdown

### Method 2: From IAM Console
1. Go to IAM service
2. Your Account ID is shown at the top

## Step 3: Update ECS Task Definition

Once you have your Account ID (example: 123456789012), I'll help you update the ECS task definition file.

## Step 4: Alternative - Use Environment Variables Instead

If you prefer not to use Secrets Manager right now, you can also pass these as environment variables directly in the ECS task definition:

```json
"environment": [
  {
    "name": "SECRET_KEY", 
    "value": "your-secret-key"
  },
  {
    "name": "DATABASE_URL",
    "value": "mysql://user:pass@rds-endpoint:3306/dbname"
  }
]
```

## Important Values You Need:

### From your RDS instance:
- **Endpoint:** Find in RDS Console → Your DB → "Connectivity & security" tab
- **Username:** What you set as master username when creating RDS
- **Password:** What you set as master password when creating RDS  
- **Database Name:** What you named your database

### Example Database URL:
If your RDS endpoint is `mydb.abc123.us-east-1.rds.amazonaws.com` and you created:
- Username: `admin`
- Password: `mypassword123`
- Database: `leavedb`

Then your DATABASE_URL would be:
`mysql://admin:mypassword123@mydb.abc123.us-east-1.rds.amazonaws.com:3306/leavedb`

---

**Which method do you prefer:**
1. **AWS Console** (create secrets through web interface) - No installation needed
2. **Environment Variables** (simpler, less secure for production)

**Tell me your AWS Account ID and RDS details, and I'll help you complete the setup!**