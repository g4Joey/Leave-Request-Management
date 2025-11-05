import os
import django
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "leave_management.settings")
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from users.models import Affiliate
from leaves.models import LeaveType, LeaveRequest
from leaves.views import ManagerLeaveViewSet
from datetime import date, timedelta

User = get_user_model()

pytestmark = pytest.mark.django_db


def _make_user(username: str, role: str, affiliate: Affiliate | None = None, **extra):
    return User.objects.create_user(
        username=username,
        password="pass12345",
        email=f"{username}@example.com",
        first_name=username.capitalize(),
        last_name="Test",
        employee_id=f"E{User.objects.count()+1000:04d}",
        role=role,
        affiliate=affiliate,
        **extra,
    )


def _make_pending_leave(emp: User, leave_type: LeaveType) -> LeaveRequest:
    today = date.today()
    lr = LeaveRequest.objects.create(
        employee=emp,
        leave_type=leave_type,
        start_date=today + timedelta(days=1),
        end_date=today + timedelta(days=1),
        reason="SBL quick leave",
        status="pending",
    )
    return lr


def test_sbl_requests_not_in_manager_pending_and_appear_in_sbl_ceo():
    # Affiliates
    sbl = Affiliate.objects.create(name="SBL")

    # Users
    ceo_sbl = _make_user("ceo_sbl", role="ceo", affiliate=sbl)
    manager_merban = _make_user("mrg_merban_b", role="manager")  # unrelated manager
    staff_sbl = _make_user("staff_sbl", role="junior_staff", affiliate=sbl)

    # Leave type and pending request for SBL staff
    annual = LeaveType.objects.create(name="Annual 2")
    lr = _make_pending_leave(staff_sbl, annual)

    factory = APIRequestFactory()

    # Manager pending_approvals should NOT include SBL items
    req_mgr = factory.get("/api/leaves/manager/pending_approvals/")
    force_authenticate(req_mgr, user=manager_merban)
    view_mgr = ManagerLeaveViewSet.as_view({"get": "pending_approvals"})
    resp_mgr = view_mgr(req_mgr)
    assert resp_mgr.status_code == 200
    ids = {r["id"] for r in resp_mgr.data["requests"]}
    assert lr.id not in ids

    # SBL CEO should see the pending in CEO queue
    req_ceo = factory.get("/api/leaves/manager/pending_approvals/")
    force_authenticate(req_ceo, user=ceo_sbl)
    view_ceo = ManagerLeaveViewSet.as_view({"get": "pending_approvals"})
    resp_ceo = view_ceo(req_ceo)
    assert resp_ceo.status_code == 200
    ids_ceo = {r["id"] for r in resp_ceo.data["requests"]}
    assert lr.id in ids_ceo
