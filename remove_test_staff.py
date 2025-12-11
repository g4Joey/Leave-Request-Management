import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

target_emails = [
    'manager@company.com',
    'hr@company.com',
    'jane.smith@company.com',
    'john.doe@company.com',
]

deleted = []
not_found = []
for email in target_emails:
    u = User.objects.filter(email__iexact=email).first()
    if not u:
        # try username fallback
        u = User.objects.filter(username__iexact=email).first()
    if u:
        deleted.append((email, u.username, u.pk))
        u.delete()
    else:
        not_found.append(email)

print('Deleted users:')
for e,u,pk in deleted:
    print(f' - {e} (username={u}, pk={pk})')
if not_found:
    print('\nNot found:')
    for e in not_found:
        print(f' - {e}')
else:
    if not deleted:
        print('No matching test users were found.')
