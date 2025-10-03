#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser

def update_user_roles():
    print("🔄 Updating user roles...")
    
    # Update Augustine to junior_staff
    try:
        augustine = CustomUser.objects.get(first_name__icontains='augustine')
        old_role = augustine.role
        augustine.role = 'junior_staff'
        augustine.save()
        print(f'✅ Augustine: {old_role} → junior_staff')
    except CustomUser.DoesNotExist:
        print('❌ Augustine not found')
    except Exception as e:
        print(f'❌ Error updating Augustine: {e}')

    # Update George Safo to senior_staff
    try:
        george = CustomUser.objects.get(first_name__icontains='george', last_name__icontains='safo')
        old_role = george.role
        george.role = 'senior_staff'
        george.save()
        print(f'✅ George Safo: {old_role} → senior_staff')
    except CustomUser.DoesNotExist:
        print('❌ George Safo not found')
    except Exception as e:
        print(f'❌ Error updating George: {e}')

    # Verify the changes
    print('\n📋 Current user roles:')
    users = CustomUser.objects.all().order_by('first_name')
    for user in users:
        print(f'  {user.first_name} {user.last_name}: {user.role}')
    
    print("\n✅ Role updates completed!")

if __name__ == '__main__':
    update_user_roles()