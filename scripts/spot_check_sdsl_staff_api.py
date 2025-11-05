import os
import sys
import django
from pathlib import Path
# Ensure project root is on PYTHONPATH
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from users.views import StaffManagementView
from users.models import Affiliate, CustomUser


def main():
    aff = Affiliate.objects.filter(name__iexact='SDSL').first()
    if not aff:
        print('SDSL affiliate not found.'); return

    # pick an HR/admin/superuser
    user = (
        CustomUser.objects.filter(is_superuser=True).first()
        or CustomUser.objects.filter(role__in=['hr', 'admin']).first()
        or CustomUser.objects.first()
    )
    if not user:
        print('No users found to authenticate with.'); return

    factory = APIRequestFactory()
    request = factory.get(f'/users/staff/?affiliate_id={aff.id}')
    force_authenticate(request, user=user)
    view = StaffManagementView.as_view()
    response = view(request)
    print('Status:', response.status_code)
    try:
        data = response.data
    except Exception:
        data = response
    # print summary
    if isinstance(data, list):
        print('Items:', len(data))
        if data:
            sample = data[0]
            print('Sample keys:', list(sample.keys()))
            print('Sample affiliate_id:', sample.get('affiliate_id'))
            print('Sample affiliate_name:', sample.get('affiliate_name'))
    else:
        print('Unexpected payload type:', type(data))
        print('Payload preview:', str(data)[:500])

if __name__ == '__main__':
    main()
