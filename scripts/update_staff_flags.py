import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
import django
django.setup()
from users.models import CustomUser
from pprint import pprint

def main():
    # Set is_staff True for all non-admin users
    updated = CustomUser.objects.exclude(email='admin@umbcapital.com').update(is_staff=True)
    print(f"is_staff set True for {updated} users")
    # Ensure admin remains staff accessible if desired (currently is_staff already True)
    admin = CustomUser.objects.filter(email='admin@umbcapital.com').first()
    if admin and not admin.is_staff:
        admin.is_staff = True  # Adjust if you actually want admin staff access
        admin.save()
        print("Admin is_staff set True (optional)")
    # Adjust enartey to senior_staff if present
    enartey = CustomUser.objects.filter(email='enartey@umbcapital.com').first()
    if enartey:
        if enartey.role != 'senior_staff':
            enartey.role = 'senior_staff'
            enartey.save()
            print('Updated enartey to senior_staff')
    users = list(CustomUser.objects.all().values('email','role','is_staff','is_superuser'))
    pprint(users)

if __name__ == '__main__':
    main()