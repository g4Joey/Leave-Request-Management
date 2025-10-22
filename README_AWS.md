AWS Free-tier Deployment Guide (Elastic Beanstalk)

This guide shows a minimal path to run the Leave Request Management app on AWS Elastic Beanstalk (EB) using the free tier. EB provides both a simple deploy experience and a secure way to run Django apps without managing servers directly.

High-level options
- Quick (free-tier testing): Use EB + a single small EC2 instance and SQLite (not for real production, but suitable for demo/testing).
- Recommended production: EB + RDS (MySQL/Postgres) — note RDS may not be free depending on usage.

Prerequisites
- AWS account (free tier eligible if within limits)
- Install AWS CLI and EB CLI
  - Windows (cmd):
    pip install --user awsebcli

1) Prepare code
- Ensure your requirements.txt is up-to-date.
- Add the provided `.ebextensions/django.config` and `leave_management/settings_aws.py`.

2) Initialize Elastic Beanstalk
- In project root (where `manage.py` sits):

```cmd
eb init -p python-3.12 leave-request-app --region us-east-1
```

- When prompted, select the existing application or create new. Choose the default IAM role prompts.

3) Create environment
- For quick free-tier testing with SQLite:

```cmd
eb create leave-req-env --single --instance_type t2.micro --envvars USE_SQLITE=1,DEBUG=True,SECRET_KEY=your-secret
```

Notes:
- `--single` creates an environment with a single instance (lower cost).
- `t2.micro` is free-tier eligible in many regions.
- `USE_SQLITE=1` makes the app use local SQLite DB stored in the instance (ephemeral; data lost on instance replacement). Good for demos only.

4) Deploy

```cmd
eb deploy
```

The `.ebextensions/django.config` will try to run migrations and collectstatic during deploy. If you set `CEO_EMAIL` and `CEO_PASSWORD` in EB environment variables, the deployment hook will attempt to create the CEO user.

5) Post-deploy
- To open the app:

```cmd
eb open
```

- To create CEO user manually (if not created automatically):

```cmd
eb ssh
# then on the instance shell
cd /var/app/current
source /var/app/venv/*/bin/activate
python manage.py create_ceo --email="ceo@yourcompany.com" --password="YourSecurePass123!"
```

6) (Optional) Add RDS
- Use the EB console to add an RDS instance. After attaching RDS, set `USE_SQLITE=0` and configure `DATABASE_URL` or DB_* env vars.

7) Security & Notes
- For real production, do NOT use SQLite. Use RDS or an external managed DB.
- Ensure `SECRET_KEY` is set to a strong secret in environment variables.
- Turn off `DEBUG` in production.
- Use S3 for user uploaded media in production.

If you'd like, I can:
- Walk you through initializing EB from your machine step-by-step.
- Prepare a production-ready RDS config and migration strategy.
- Help you run the EB CLI commands from this environment if you give permission to run the terminal commands.

