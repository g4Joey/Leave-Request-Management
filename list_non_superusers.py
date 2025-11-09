from django.conf import settings
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','leave_management.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
import json
U=get_user_model()
emails=list(U.objects.filter(is_superuser=False).values_list('email', flat=True))
print(json.dumps(emails))
