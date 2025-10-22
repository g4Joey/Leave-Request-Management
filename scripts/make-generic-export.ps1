Param(
  [string]$Dest = "generic_export"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host "Creating clean export at '$Dest'..."
if (Test-Path $Dest) { Remove-Item -Recurse -Force $Dest }
New-Item -ItemType Directory -Path $Dest | Out-Null

# Items to include (local + DigitalOcean only)
$includeDirs = @(
  'leave_management',
  'leaves',
  'users',
  'notifications',
  'templates',
  'frontend'
)
$includeFiles = @(
  'manage.py',
  'requirements.txt',
  'Dockerfile',
  'docker-compose.yml',
  'docker-compose.prod.yml',
  'nginx.prod.conf',
  'entrypoint.sh',
  'README_DOCKER.md',
  'PRODUCTION_DOCKER_GUIDE.md'
)

foreach ($d in $includeDirs) {
  if (Test-Path $d) {
    Write-Host "Copying directory: $d"
    Copy-Item -Recurse -Force $d -Destination (Join-Path $Dest $d)
  }
}
foreach ($f in $includeFiles) {
  if (Test-Path $f) {
    Write-Host "Copying file: $f"
    Copy-Item -Force $f -Destination (Join-Path $Dest $f)
  }
}

# Remove excluded platform-specific artifacts
Write-Host "Removing platform-specific (AWS/Render/Railway) files..."
$excludePaths = @(
  'leave_management/settings_aws.py',
  '.ebextensions',
  '.github/workflows',
  'railway.json',
  'Procfile',
  'ecs-task-definition.json',
  'ecs-task-definition-simple.json',
  'deploy-to-aws.bat'
)
$excludePatterns = @(
  'AWS_*',
  'README_AWS.md',
  'MANUAL_AWS_SETUP.md',
  'PRODUCTION_DEPLOYMENT_GUIDE.md',
  'RDS_SECURITY_SETUP.md',
  'AWS_CLOUDSHELL_DEPLOYMENT_GUIDE.md',
  'AWS_SECRETS_GUIDE.md'
)
foreach ($p in $excludePaths) {
  $full = Join-Path $Dest $p
  if (Test-Path $full) {
    Remove-Item -Recurse -Force $full
  }
}
Get-ChildItem -Path $Dest -Recurse -Force -ErrorAction SilentlyContinue |
  Where-Object { $name = $_.Name; $excludePatterns | ForEach-Object { if ($name -like $_) { $true } } } |
  ForEach-Object { Remove-Item -Recurse -Force $_.FullName }

# Remove dev/build artifacts and backups
Write-Host "Removing dev/build artifacts..."
$artifactPatterns = @(
  'db.sqlite3',
  '*.sqlite3',
  'data-backup-*.json',
  'leave-app*.tar*',
  '*.zip',
  '__pycache__',
  '*.pyc'
)
Get-ChildItem -Path $Dest -Recurse -Force -ErrorAction SilentlyContinue |
  Where-Object { $n = $_.Name; $artifactPatterns | ForEach-Object { if ($n -like $_) { $true } } } |
  ForEach-Object { Remove-Item -Recurse -Force $_.FullName }

# Create .gitignore in export
$gitignore = @'
# Python
__pycache__/
*.py[cod]
*.sqlite3

# Node
frontend/node_modules/
frontend/.cache/
frontend/build/

# Docker artifacts
*.tar
*.tar.gz

# OS/Editor
.DS_Store
Thumbs.db
*.swp

# Env files
.env
.env.*
'@
Set-Content -Path (Join-Path $Dest '.gitignore') -Value $gitignore -NoNewline

# Create README.md (generic)
$readme = @'
# Leave Request Management (Generic)

This is a generic, unbranded version of the Leave Request Management app.
It includes only local development and DigitalOcean deployment assets.

## Quick start (local)

```bash
# 1) Create virtualenv (optional) and install dependencies
python -m venv .venv
. .venv/Scripts/activate  # on Windows
pip install -r requirements.txt

# 2) Run database migrations and start server
python manage.py migrate
python manage.py runserver
```

## Docker (local)

```bash
# Build and run
docker build -t leave-request-app:latest .
# With compose (local)
docker compose up --build
```

## DigitalOcean App Platform

- Build from Dockerfile at repo root
- Expose port 8000 (Gunicorn in entrypoint binds to 0.0.0.0:8000)
- Set environment variables:
  - DJANGO_SETTINGS_MODULE=leave_management.settings_production
  - SECRET_KEY=your-production-secret
  - DATABASE_URL=mysql://USER:PASS@HOST:3306/DBNAME  (Managed MySQL)
  - RUN_SEED_ON_DEPLOY=1 (optional) to seed initial users

Ensure you add a Managed MySQL database and link it (prefer SSL required).
'@
Set-Content -Path (Join-Path $Dest 'README.md') -Value $readme -NoNewline

Write-Host "Export staged at" (Resolve-Path $Dest)
