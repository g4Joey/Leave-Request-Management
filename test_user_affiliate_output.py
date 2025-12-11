import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from users.serializers import UserSerializer
import json

u = CustomUser.objects.filter(email__icontains='jmankoe').first() or CustomUser.objects.first()
ser = UserSerializer(u)
print(json.dumps(ser.data, indent=2, default=str))
