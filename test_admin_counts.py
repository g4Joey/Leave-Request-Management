#!/usr/bin/env python
import os, sys, django
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from users.models import CustomUser
from leaves.views import ManagerLeaveViewSet
from django.test import RequestFactory
from rest_framework.request import Request

"""Call approval_counts as admin and print the JSON returned vs computed subsets."""

def call_endpoint(user):
    factory = RequestFactory()
    req = factory.get('/leaves/manager/approval_counts/')
    req.user = user
    vs = ManagerLeaveViewSet(); vs.request = Request(req)
    resp = vs.approval_counts(vs.request)
    print('Endpoint JSON:', resp.data)

if __name__ == '__main__':
    admin = CustomUser.objects.filter(is_superuser=True).first() or CustomUser.objects.filter(role='admin').first()
    if not admin:
        print('No admin available')
    else:
        print(f'Admin: {admin.username} ({admin.email})')
        call_endpoint(admin)
