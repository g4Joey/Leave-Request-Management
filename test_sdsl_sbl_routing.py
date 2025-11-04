import os
import django
import pytest

# Configure Django settings for pytest without pytest.ini
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
        employee_id=f"E{User.objects.count()+1:04d}",
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
        end_date=today + timedelta(days=2),
        reason="Short break",
        status="pending",
    )
    return lr


def test_sdsl_requests_not_in_manager_pending_and_appear_in_ceo():
    # Affiliates
    sdsl = Affiliate.objects.create(name="SDSL")

    # Users
    ceo_sdsl = _make_user("ceo_sdsl", role="ceo", affiliate=sdsl)
    manager_merban = _make_user("mrg_merban", role="manager")  # unrelated manager
    staff_sdsl = _make_user("staff_sdsl", role="junior_staff", affiliate=sdsl)

    # Leave type and pending request for SDSL staff
    annual = LeaveType.objects.create(name="Annual")
    lr = _make_pending_leave(staff_sdsl, annual)

    factory = APIRequestFactory()

    # 1) Manager pending_approvals should NOT include SDSL items
    req_mgr = factory.get("/api/leaves/manager/pending_approvals/")
    force_authenticate(req_mgr, user=manager_merban)
    view_mgr = ManagerLeaveViewSet.as_view({"get": "pending_approvals"})
    resp_mgr = view_mgr(req_mgr)
    assert resp_mgr.status_code == 200
    payload_mgr = resp_mgr.data
    assert payload_mgr["user_role"] == "manager"
    # Ensure our SDSL request is not listed
    ids = {r["id"] for r in payload_mgr["requests"]}
    assert lr.id not in ids

    # 2) SDSL CEO should see the pending in CEO queue
    req_ceo = factory.get("/api/leaves/manager/pending_approvals/")
    force_authenticate(req_ceo, user=ceo_sdsl)
    view_ceo = ManagerLeaveViewSet.as_view({"get": "pending_approvals"})
    resp_ceo = view_ceo(req_ceo)
    assert resp_ceo.status_code == 200
    payload_ceo = resp_ceo.data
    assert payload_ceo["user_role"] == "ceo"
    ids_ceo = {r["id"] for r in payload_ceo["requests"]}
    assert lr.id in ids_ceo, "SDSL pending request should be visible to SDSL CEO"

    # 3) Optionally validate categorized CEO endpoint returns it under 'staff'
    req_ceo_cat = factory.get("/api/leaves/manager/ceo_approvals_categorized/")
    force_authenticate(req_ceo_cat, user=ceo_sdsl)
    view_ceo_cat = ManagerLeaveViewSet.as_view({"get": "ceo_approvals_categorized"})
    resp_ceo_cat = view_ceo_cat(req_ceo_cat)
    assert resp_ceo_cat.status_code == 200
    data_cat = resp_ceo_cat.data
    assert data_cat["ceo_affiliate"] == "SDSL"
    assert data_cat["total_count"] >= 1
    staff_items = data_cat["categories"]["staff"]
    assert any(item["id"] == lr.id for item in staff_items)
