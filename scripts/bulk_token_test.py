import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
import django
django.setup()
import requests
from users.models import CustomUser

BASE = 'http://127.0.0.1:8000/api/auth/token/'
# Assuming all test accounts share the same seeded password
DEFAULT_PASSWORD = 'AdminChangeMe123!'

def main():
    rows = []
    for u in CustomUser.objects.all():
        try:
            r = requests.post(BASE, json={'username': u.email, 'password': DEFAULT_PASSWORD}, timeout=5)
            rows.append((u.email, u.role, r.status_code))
            print(f"{u.email} -> {r.status_code}")
        except Exception as e:
            rows.append((u.email, u.role, f'ERR:{e.__class__.__name__}'))
            print(f"{u.email} -> ERR {e}")
    # Summary
    success = [r for r in rows if r[2] == 200]
    failed = [r for r in rows if r[2] != 200]
    print("\n=== Token Test Summary ===")
    print(f"Successful ({len(success)}):")
    for r in success: print("  ", r)
    print(f"Failed ({len(failed)}):")
    for r in failed: print("  ", r)
    if failed:
        print("\nRun password reset script if needed.")

if __name__ == '__main__':
    main()