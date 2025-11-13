#!/usr/bin/env python
"""
Quick end-to-end checks for:
1) HR Approval Records grouping by affiliate
2) Merban CEO pending tabs/categories
3) SDSL/SBL CEO: only Staff tab for both pending and records

Runs against ViewSet actions using DRF RequestFactory, no server needed.
"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')

import django
django.setup()

from django.test import RequestFactory
from rest_framework.request import Request
from rest_framework.response import Response

from users.models import CustomUser
from leaves.views import ManagerLeaveViewSet


def get_user_by_role(role: str, affiliate_names=None, email_hint=None):
    qs = CustomUser.objects.filter(role=role, is_active=True)
    if email_hint:
        u = CustomUser.objects.filter(email=email_hint).first()
        if u:
            return u
    if affiliate_names:
        qs = qs.filter(affiliate__name__in=affiliate_names)
    return qs.first()


def call_action(viewset_cls, action_name: str, user, path: str):
    factory = RequestFactory()
    http_request = factory.get(path)
    http_request.user = user
    viewset = viewset_cls()
    viewset.request = Request(http_request)
    viewset.format_kwarg = None
    action = getattr(viewset, action_name)
    resp = action(viewset.request)
    assert isinstance(resp, Response), f"Unexpected response type for {action_name}"
    return resp


def check_hr_records():
    print("\n=== HR Approval Records grouped by affiliate ===")
    hr_user = get_user_by_role('hr')
    if not hr_user:
        print("! No HR user found")
        return
    resp = call_action(ManagerLeaveViewSet, 'approval_records', hr_user, '/leaves/manager/approval_records/')
    print(f"Status: {resp.status_code}")
    data = resp.data or {}
    print(f"Role: {data.get('role')}")
    groups = data.get('groups', {})
    for key in ['Merban Capital', 'SDSL', 'SBL', 'Other']:
        print(f"  {key}: {len(groups.get(key, []))}")


def check_merban_ceo():
    print("\n=== Merban CEO pending categories + records ===")
    ceo = get_user_by_role('ceo', affiliate_names=['MERBAN CAPITAL', 'Merban Capital'], email_hint='ceo@umbcapital.com')
    if not ceo:
        print("! No Merban CEO found")
        return
    # Pending (categorized)
    resp = call_action(ManagerLeaveViewSet, 'ceo_approvals_categorized', ceo, '/leaves/manager/ceo_approvals_categorized/')
    print(f"Pending: status={resp.status_code}, counts={resp.data.get('counts', {})}")
    # Records (grouped by submitter category)
    resp2 = call_action(ManagerLeaveViewSet, 'approval_records', ceo, '/leaves/manager/approval_records/')
    groups = resp2.data.get('groups', {})
    print("Records groups:")
    for key in ['hod_manager', 'hr', 'staff']:
        print(f"  {key}: {len(groups.get(key, []))}")


def check_sdsl_sbl_ceo():
    print("\n=== SDSL/SBL CEO: only Staff tab (pending + records) ===")
    for aff, email in [("SDSL", 'sdslceo@umbcapital.com'), ("SBL", 'sblceo@umbcapital.com')]:
        ceo = get_user_by_role('ceo', affiliate_names=[aff], email_hint=email)
        if not ceo:
            print(f"! No {aff} CEO found")
            continue
        resp = call_action(ManagerLeaveViewSet, 'ceo_approvals_categorized', ceo, '/leaves/manager/ceo_approvals_categorized/')
        counts = resp.data.get('counts', {})
        print(f"{aff} Pending counts: {counts}")
        # Records
        resp2 = call_action(ManagerLeaveViewSet, 'approval_records', ceo, '/leaves/manager/approval_records/')
        groups = resp2.data.get('groups', {})
        print(f"{aff} Records counts: hod_manager={len(groups.get('hod_manager', []))}, hr={len(groups.get('hr', []))}, staff={len(groups.get('staff', []))}")


if __name__ == '__main__':
    try:
        check_hr_records()
        check_merban_ceo()
        check_sdsl_sbl_ceo()
        print("\n✅ Quick end-to-end checks completed")
    except Exception as e:
        print(f"\n❌ Error during checks: {e}")
        import traceback
        traceback.print_exc()
