import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

email = 'hradmin@umbcapital.com'
new_password = '1HRADMIN'

user = User.objects.filter(email__iexact=email).first()
if not user:
    user = User.objects.filter(username__iexact=email).first()

if user:
    user.set_password(new_password)
    user.save()
    print(f"Password reset for {user.email}")
else:
    print('HR user not found')
