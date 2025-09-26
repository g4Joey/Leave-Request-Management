web: gunicorn leave_management.wsgi:application --bind 0.0.0.0:$PORT
# Release phase now ONLY runs migrations and a DB verification check.
# Seeding (setup_production_data) must be invoked manually if desired after initial data load.
release: python manage.py migrate && python manage.py verify_db