#!/usr/bin/env python3
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from leaves.views import LeaveRequestViewSet
from rest_framework.test import force_authenticate

User = get_user_model()
user = User.objects.get(username='aakorfu')
print('Testing approval_counts for user', user.username)
factory = RequestFactory()
request = factory.get('/leaves/requests/approval_counts/')
force_authenticate(request, user=user)
view = LeaveRequestViewSet.as_view({'get':'approval_counts'})
import sys as _sys
print('LeaveRequestViewSet module:', LeaveRequestViewSet.__module__)
mod = _sys.modules.get(LeaveRequestViewSet.__module__)
print('Module file:', getattr(mod, '__file__', 'unknown'))
print('Has approval_counts attribute on class:', hasattr(LeaveRequestViewSet, 'approval_counts'))
print('Callable approval_counts attr:', callable(getattr(LeaveRequestViewSet, 'approval_counts', None)))
print('Approval-like attributes on class:', [n for n in dir(LeaveRequestViewSet) if 'approval' in n.lower()])
print('Some class attributes:', [n for n in dir(LeaveRequestViewSet) if not n.startswith('_')][:80])

response = view(request)
print('Status:', response.status_code)
print('Data:', response.data)
