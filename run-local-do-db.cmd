@echo off
REM Run locally against DigitalOcean Managed MySQL using production settings
SETLOCAL ENABLEDELAYEDEXPANSION

REM Use production settings to enable DATABASE_URL parsing and SSL
set DJANGO_SETTINGS_MODULE=leave_management.settings_production
set DEBUG=True

REM IMPORTANT: set DATABASE_URL to your DO connection string first.
REM Example (replace placeholders):
REM   mysql://doadmin:YOUR_PASSWORD@YOUR-DO-HOST:25060/defaultdb?ssl-mode=REQUIRED

if "%DATABASE_URL%"=="" (
  echo.
  echo ERROR: DATABASE_URL is not set.
  echo Please set it to your DigitalOcean connection string, e.g.:
  echo   set DATABASE_URL=mysql://doadmin:YOUR_PASSWORD@YOUR-DO-HOST:25060/defaultdb?ssl-mode=REQUIRED
  echo Then run this script again.
  exit /b 2
)

REM Allow local frontend origins if you use a separate UI
if "%CORS_ALLOWED_ORIGINS%"=="" set CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

REM Optional: show which DB settings Django sees
python manage.py show_db || goto :error

REM Connectivity diagnostics (DNS/TCP/SSL/SELECT 1)
python manage.py check_db --retries 2 --delay 1 || goto :error

REM Apply migrations and run
python manage.py migrate || goto :error
python manage.py runserver
exit /b %ERRORLEVEL%

:error
 echo Failed. See errors above.
 exit /b 1
