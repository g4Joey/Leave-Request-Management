import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()
import pytest
from django.utils import timezone
from datetime import timedelta
from users.models import Affiliate, Department, CustomUser
from leaves.models import LeaveType, LeaveRequest
from leaves.services import ApprovalWorkflowService


@pytest.mark.django_db
def test_affiliate_routing_lightweight():
    # Affiliates
    merban, _ = Affiliate.objects.get_or_create(name='MERBAN CAPITAL')
    sdsl, _ = Affiliate.objects.get_or_create(name='SDSL')
    sbl, _ = Affiliate.objects.get_or_create(name='SBL')

    # Leave type
    lt, _ = LeaveType.objects.get_or_create(name='Annual')

    # Merban department
    merban_dept, _ = Department.objects.get_or_create(name='Finance & Accounts', affiliate=merban)

    # Users
    merban_ceo = CustomUser.objects.create_user(
        username='merban_ceo_lw', email='merban.ceo.lw@example.com', password='password123',
        first_name='Merban', last_name='CEO', employee_id='MB-CEO-LW', role='ceo', affiliate=merban
    )
    sdsl_ceo = CustomUser.objects.create_user(
        username='sdsl_ceo_lw', email='sdsl.ceo.lw@example.com', password='password123',
        first_name='SDSL', last_name='CEO', employee_id='SDSL-CEO-LW', role='ceo', affiliate=sdsl
    )
    sbl_ceo = CustomUser.objects.create_user(
        username='sbl_ceo_lw', email='sbl.ceo.lw@example.com', password='password123',
        first_name='SBL', last_name='CEO', employee_id='SBL-CEO-LW', role='ceo', affiliate=sbl
    )

    merban_manager = CustomUser.objects.create_user(
        username='merban_mgr_lw', email='merban.manager.lw@example.com', password='password123',
        first_name='Merban', last_name='Manager', employee_id='MB-MGR-LW', role='manager', affiliate=merban,
        department=merban_dept
    )

    # Staff
    sdsl_staff = CustomUser.objects.create_user(
        username='sdsl_staff_lw', email='sdsl.staff.lw@example.com', password='password123',
        first_name='SDSL', last_name='Staff', employee_id='SDSL-STF-LW', role='junior_staff', affiliate=sdsl
    )
    sbl_staff = CustomUser.objects.create_user(
        username='sbl_staff_lw', email='sbl.staff.lw@example.com', password='password123',
        first_name='SBL', last_name='Staff', employee_id='SBL-STF-LW', role='junior_staff', affiliate=sbl
    )
    merban_staff = CustomUser.objects.create_user(
        username='merban_staff_lw', email='merban.staff.lw@example.com', password='password123',
        first_name='Merban', last_name='Staff', employee_id='MB-STF-LW', role='junior_staff', affiliate=merban,
        department=merban_dept
    )

    future_start = timezone.now().date() + timedelta(days=7)
    future_end = future_start + timedelta(days=2)

    # Leave requests
    lr_sdsl = LeaveRequest.objects.create(
        employee=sdsl_staff, leave_type=lt, start_date=future_start, end_date=future_end, status='pending'
    )
    lr_sbl = LeaveRequest.objects.create(
        employee=sbl_staff, leave_type=lt, start_date=future_start, end_date=future_end, status='pending'
    )
    lr_merban_hr = LeaveRequest.objects.create(
        employee=merban_staff, leave_type=lt, start_date=future_start, end_date=future_end, status='hr_approved'
    )

    # 1) SDSL/SBL pending aren’t in manager queues -> manager cannot approve
    assert ApprovalWorkflowService.can_user_approve(lr_sdsl, merban_manager) is False
    assert ApprovalWorkflowService.can_user_approve(lr_sbl, merban_manager) is False

    # 2) SDSL/SBL pending appear for the correct CEO only
    assert ApprovalWorkflowService.can_user_approve(lr_sdsl, sdsl_ceo) is True
    assert ApprovalWorkflowService.can_user_approve(lr_sdsl, sbl_ceo) is False
    assert ApprovalWorkflowService.can_user_approve(lr_sdsl, merban_ceo) is False

    assert ApprovalWorkflowService.can_user_approve(lr_sbl, sbl_ceo) is True
    assert ApprovalWorkflowService.can_user_approve(lr_sbl, sdsl_ceo) is False
    assert ApprovalWorkflowService.can_user_approve(lr_sbl, merban_ceo) is False

    # 3) Merban hr_approved appear only for Merban CEO
    assert ApprovalWorkflowService.can_user_approve(lr_merban_hr, merban_ceo) is True
    assert ApprovalWorkflowService.can_user_approve(lr_merban_hr, sdsl_ceo) is False
    assert ApprovalWorkflowService.can_user_approve(lr_merban_hr, sbl_ceo) is False
