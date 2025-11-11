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

def main():
    ceo = CustomUser.objects.filter(email='ceo@umbcapital.com').first()
    if not ceo:
        print('No ceo@umbcapital.com user found')
        return
    print(f"CEO: {ceo.username} role={getattr(ceo,'role',None)} affiliate={getattr(ceo,'affiliate',None)}")

    factory = RequestFactory()
    http = factory.get('/leaves/manager/')
    http.user = ceo
    vs = ManagerLeaveViewSet(); vs.request = Request(http)
    qs = vs.get_queryset()
    print('CEO-visible queryset count:', qs.count())
    for lr in qs[:10]:
        print(f"  ID {lr.id} {lr.employee.username} status={lr.status}")

if __name__ == '__main__':
    main()
