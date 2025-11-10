#!/usr/bin/env python
import os, sys, django
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from rest_framework.test import APIClient
from leaves.models import LeaveRequest


def summary(label, value):
    print(f"{label}: {value}")

def run():
    print("=== CEO NEW ENDPOINT TEST ===")
    # Merban CEO
    merban_ceo = CustomUser.objects.filter(email='ceo@umbcapital.com').first()
    if not merban_ceo:
        print("Merban CEO not found")
        return
    client = APIClient()
    client.force_authenticate(user=merban_ceo)
    resp = client.get('/leaves/ceo/approvals_categorized/')
    summary('Merban categorized status', resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        summary('Merban total_count', data.get('total_count'))
        summary('Merban affiliate', data.get('ceo_affiliate'))
        summary('Staff count', data.get('counts', {}).get('staff'))
    else:
        print(resp.content[:200])

    # SDSL CEO
    sdsl_ceo = CustomUser.objects.filter(email__icontains='sdsl').filter(role='ceo').first()
    if sdsl_ceo:
        client2 = APIClient(); client2.force_authenticate(user=sdsl_ceo)
        resp2 = client2.get('/leaves/ceo/approvals_categorized/')
        summary('SDSL categorized status', resp2.status_code)
    else:
        print('SDSL CEO not present for test')

    # SBL CEO
    sbl_ceo = CustomUser.objects.filter(email__icontains='sbl').filter(role='ceo').first()
    if sbl_ceo:
        client3 = APIClient(); client3.force_authenticate(user=sbl_ceo)
        resp3 = client3.get('/leaves/ceo/approvals_categorized/')
        summary('SBL categorized status', resp3.status_code)
    else:
        print('SBL CEO not present for test')

    # Approve flow smoke test (Merban)
    pending_merban = LeaveRequest.objects.filter(status='hr_approved').first()
    if pending_merban:
        approve_resp = client.put(f'/leaves/ceo/{pending_merban.id}/approve/', {'approval_comments': 'CEO final approve (test)'})
        summary('Approve response code', approve_resp.status_code)
        if approve_resp.status_code == 200:
            summary('New status', approve_resp.json().get('new_status'))
    else:
        print('No hr_approved request found for Merban CEO approve test')

if __name__ == '__main__':
    run()
