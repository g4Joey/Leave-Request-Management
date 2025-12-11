import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
import django
django.setup()
from users.models import CustomUser

DEFAULT_PASSWORD = 'StaffPass123!'
EXCLUDE = {'admin@umbcapital.com'}  # keep admin separate if desired

def main():
    to_update = CustomUser.objects.exclude(email__in=EXCLUDE)
    count = 0
    for u in to_update:
        u.set_password(DEFAULT_PASSWORD)
        u.save()
        count += 1
    print(f"Reset password for {count} users to '{DEFAULT_PASSWORD}'.")
    print("Test one example with: curl -X POST -H 'Content-Type: application/json' -d '{\"username\":\"aakorfu@umbcapital.com\",\"password\":\"StaffPass123!\"}' http://127.0.0.1:8000/api/auth/token/")

if __name__ == '__main__':
    main()