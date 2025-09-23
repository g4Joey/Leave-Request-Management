web: gunicorn leave_management.wsgi:application --bind 0.0.0.0:$PORT
release: python manage.py migrate && python manage.py setup_production_data