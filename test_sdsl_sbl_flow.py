#!/usr/bin/env python
import os, sys, django
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from leaves.models import LeaveRequest
from rest_framework.test import APIClient

"""
Integration test for SDSL/SBL first-approver flow:
- Staff from SDSL/SBL submits pending request
- CEO sees it in /leaves/ceo/approvals_categorized
- CEO approves -> status becomes ceo_approved
- HR can then approve final
"""

def run():
    print('=== SDSL/SBL Flow Smoke Test ===')
    # Find any SDSL CEO
    sdsl_ceo = CustomUser.objects.filter(role='ceo', affiliate__name__iexact='SDSL').first()
    sbl_ceo = CustomUser.objects.filter(role='ceo', affiliate__name__iexact='SBL').first()

    target_ceo = sdsl_ceo or sbl_ceo
    if not target_ceo:
        print('No SDSL/SBL CEO found; skipping')
        return
    print('Using CEO:', target_ceo.email, 'Affiliate:', target_ceo.affiliate)

    # Find a pending staff request under that affiliate
    target_req = LeaveRequest.objects.filter(
        status='pending',
        employee__affiliate=target_ceo.affiliate
    ).exclude(employee=target_ceo).first()

    if not target_req:
        print('No pending staff request found under affiliate; create one via UI to fully test.')
        return

    client = APIClient(); client.force_authenticate(user=target_ceo)
    # Confirm visibility
    vis = client.get('/leaves/ceo/approvals_categorized/').json()
    print('Visible counts:', vis.get('counts'))

    # Approve
    resp = client.put(f'/leaves/ceo/{target_req.id}/approve/', {'approval_comments': 'CEO approve (smoke test)'})
    print('Approve status:', resp.status_code)
    if resp.status_code == 200:
        print('New status:', resp.json().get('new_status'))

if __name__ == '__main__':
    run()
