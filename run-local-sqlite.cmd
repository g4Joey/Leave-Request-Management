@echo off
REM Quick local run using SQLite (no MySQL required)
SETLOCAL ENABLEDELAYEDEXPANSION

REM Use base settings with SQLite fallback
set DJANGO_SETTINGS_MODULE=leave_management.settings
set USE_SQLITE=1
set DEBUG=True

 echo Using settings: %DJANGO_SETTINGS_MODULE%
 echo Using SQLite DB at db.sqlite3

REM Optional: ensure deps
REM python -m pip install -r requirements.txt

python manage.py migrate || goto :error
python manage.py runserver
exit /b %ERRORLEVEL%

:error
 echo Failed. See errors above.
 exit /b 1
