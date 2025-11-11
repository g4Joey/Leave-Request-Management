#!/usr/bin/env python
import os, sys, django
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from leaves.models import LeaveRequest
from leaves.views import ManagerLeaveViewSet
from django.test import RequestFactory
from rest_framework.request import Request

"""Compare admin approval_counts with actual querysets by status."""

def main():
    admin = CustomUser.objects.filter(is_superuser=True).first() or CustomUser.objects.filter(role='admin').first()
    if not admin:
        print('No admin/superuser user found.')
        return
    print(f"Using admin: {admin.username} ({admin.email}) role={getattr(admin,'role',None)} superuser={admin.is_superuser}")

    factory = RequestFactory()
    req = factory.get('/leaves/manager/approval_counts/')
    req.user = admin
    vs = ManagerLeaveViewSet()
    vs.request = Request(req)

    # Emulate approval_counts logic manually
    qs = vs.get_queryset()  # For admin/superuser returns all
    pending = qs.filter(status='pending').count()
    hr_pool = qs.filter(status__in=['manager_approved','ceo_approved']).count()
    ceo_pool = qs.filter(status='hr_approved').count()
    total_calc = pending + hr_pool + ceo_pool

    print('\nRaw calculated counts:')
    print(f" pending: {pending}\n hr_stage: {hr_pool}\n ceo_stage: {ceo_pool}\n total: {total_calc}")

    print('\nSample listings by stage:')
    def list_subset(label, subset_qs):
        print(f"-- {label} ({subset_qs.count()} items)")
        for lr in subset_qs[:10]:
            print(f"   ID {lr.id} employee={lr.employee.username} status={lr.status}")
    list_subset('Pending', qs.filter(status='pending'))
    list_subset('Manager Approved', qs.filter(status='manager_approved'))
    list_subset('CEO Approved', qs.filter(status='ceo_approved'))
    list_subset('HR Approved', qs.filter(status='hr_approved'))

    # Cross-check if any are invisible to UI listing endpoints (simulate CEO/HR/Manager filters)
    print('\nCross-check visibility under other roles:')
    for role in ['manager','hr','ceo']:
        dummy = admin  # reuse user but temporarily patch role for check
        original_role = getattr(dummy,'role',None)
        setattr(dummy,'role',role)
        req2 = factory.get('/leaves/manager/')
        req2.user = dummy
        vs2 = ManagerLeaveViewSet(); vs2.request = Request(req2)
        role_qs = vs2.get_queryset()
        print(f" role={role} queryset_count={role_qs.count()}")
        setattr(dummy,'role',original_role)

if __name__ == '__main__':
    main()
