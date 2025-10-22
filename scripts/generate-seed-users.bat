@echo off
REM Generate SEED_USERS JSON from local/seed_users.json for production deployment

echo 🔧 Generating production user seeding configuration...

if exist "local\seed_users.json" (
    echo Generated SEED_USERS environment variable:
    echo.
    type local\seed_users.json
    echo.
    echo The above users will be seeded on deployment.
    echo I've already added them to .env.production as a single-line SEED_USERS variable.
) else (
    echo ❌ local\seed_users.json not found!
    echo Create this file with your user data first.
)

echo.
echo Users configured for seeding:
echo - Ato Mankoe (jmankoe) - manager in IT  
echo - Augustine Akorfu (aakorfu) - staff in IT
echo - George Safo (gsafo) - staff in IT
echo - CEO user from CEO_EMAIL/CEO_PASSWORD
echo - HR Admin from HR_ADMIN_* variables
pause