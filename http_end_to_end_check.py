#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from rest_framework_simplejwt.tokens import RefreshToken
import requests


def get_token_for(user):
    return str(RefreshToken.for_user(user).access_token)


def pick_user(role, email_hint=None, affiliate=None):
    qs = CustomUser.objects.filter(role=role, is_active=True)
    if email_hint:
        u = CustomUser.objects.filter(email=email_hint).first()
        if u:
            return u
    if affiliate:
        qs = qs.filter(affiliate__name__iexact=affiliate)
    return qs.first()


def hr_records(base):
    hr = pick_user('hr')
    if not hr:
        print("! No HR user found")
        return
    token = get_token_for(hr)
    headers = { 'Authorization': f'Bearer {token}' }
    r = requests.get(f"{base}/leaves/manager/approval_records/", headers=headers)
    print("HR records status:", r.status_code)
    if r.ok:
        data = r.json()
        groups = data.get('groups', {})
        print("HR groups:")
        for k in ['Merban Capital', 'SDSL', 'SBL', 'Other']:
            print(f"  {k}: {len(groups.get(k, []))}")


def ceo_checks(base, affiliate, email_hint=None):
    ceo = pick_user('ceo', email_hint=email_hint, affiliate=affiliate)
    if not ceo:
        print(f"! No CEO found for {affiliate}")
        return
    token = get_token_for(ceo)
    headers = { 'Authorization': f'Bearer {token}' }

    # Pending categorized
    r = requests.get(f"{base}/leaves/manager/ceo_approvals_categorized/", headers=headers)
    print(f"{affiliate} pending categorized status:", r.status_code)
    if r.ok:
        print(" counts:", r.json().get('counts', {}))

    # Records grouped by submitter category
    r2 = requests.get(f"{base}/leaves/manager/approval_records/", headers=headers)
    print(f"{affiliate} records status:", r2.status_code)
    if r2.ok:
        groups = r2.json().get('groups', {})
        print(" groups:", { 'hod_manager': len(groups.get('hod_manager', [])), 'hr': len(groups.get('hr', [])), 'staff': len(groups.get('staff', [])) })


if __name__ == '__main__':
    base = os.environ.get('BASE_URL', 'http://127.0.0.1:8000')
    print("Using base:", base)
    hr_records(base)
    ceo_checks(base, 'MERBAN CAPITAL', email_hint='ceo@umbcapital.com')
    ceo_checks(base, 'SDSL', email_hint='sdslceo@umbcapital.com')
    ceo_checks(base, 'SBL', email_hint='sblceo@umbcapital.com')
    print("Done.")
