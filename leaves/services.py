"""
Leave management services implementing business logic with OOP patterns.

Uses Strategy Pattern and Inheritance for different approval workflows.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from django.db import models, transaction
import logging
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.contrib.auth import get_user_model
from users.models import Affiliate, CustomUser


User = get_user_model()


class ApprovalRoutingService:
    """
    Encapsulates CEO routing logic based on employee's affiliate (with Merban department override).
    """
    
    @classmethod
    def get_ceo_for_employee(cls, employee: CustomUser) -> Optional[CustomUser]:
        """Determine the appropriate CEO strictly by affiliate (no fallback).

        Rules (case-insensitive):
        - Merban Capital: employees (including those in any Merban department) → Merban CEO
        - SDSL: employees → SDSL CEO
        - SBL: employees → SBL CEO
        - Missing/No affiliate → None (request will not appear in any CEO queue until data is fixed)

        CEOs are attached to Affiliates (not departments). Only Merban uses departments.
        """
        logger = logging.getLogger('leaves')

        if not employee:
            return None

        affiliate = getattr(employee, 'affiliate', None)

        # Merban-only department override: if no user affiliate but department affiliate is Merban, adopt it
        try:
            if not affiliate and getattr(employee, 'department', None) and getattr(employee.department, 'affiliate', None):
                dep_aff = employee.department.affiliate
                name = (getattr(dep_aff, 'name', '') or '').strip().lower()
                if name in ('merban capital', 'merban'):
                    affiliate = dep_aff
        except Exception as e:
            logger.exception("Failed department affiliate override for employee %s: %s", getattr(employee, 'id', None), e)

        if not affiliate:
            return None

        # CEOs are looked up strictly by affiliate name (with synonym grouping for Merban)
        try:
            aff_name = (getattr(affiliate, 'name', '') or '').strip().upper()
            if aff_name in ('MERBAN', 'MERBAN CAPITAL'):
                aff_names = ['MERBAN', 'MERBAN CAPITAL']
            elif aff_name == 'SDSL':
                aff_names = ['SDSL']
            elif aff_name == 'SBL':
                aff_names = ['SBL']
            else:
                aff_names = [getattr(affiliate, 'name', '')]
            ceo = (
                User.objects.filter(role__iexact='ceo', is_active=True)
                .filter(affiliate__name__in=aff_names)
                .order_by('id')
            ).first()
            return ceo
        except Exception as e:
            logger.exception("Failed to determine CEO for employee %s: %s", getattr(employee, 'id', None), e)
            return None
    
    # Removed fallback helper: strict routing only; requests with missing affiliate yield None
    
    @classmethod
    def get_employee_affiliate_name(cls, employee: CustomUser) -> str:
        """Get the affiliate name for an employee, or '' if none.

        Strict mode: We do not fabricate a placeholder affiliate. Missing or unknown affiliate
        should prevent routing/approval until data is corrected. Previously a 'DEFAULT' fallback
        implicitly treated requests as Merban; this has been removed.
        """
        if not employee:
            return ''
        # Prefer department affiliate for Merban department override (matches CEO routing logic)
        if (
            hasattr(employee, 'department') and employee.department and 
            hasattr(employee.department, 'affiliate') and employee.department.affiliate
        ):
            return (employee.department.affiliate.name or '').strip().upper()
        # Fall back to user's own affiliate if present
        if hasattr(employee, 'affiliate') and getattr(employee, 'affiliate', None):
            return (employee.affiliate.name or '').strip().upper()
        return ''


class ApprovalHandler(ABC):
    """
    Abstract base class for leave approval handlers.
    Implements Template Method pattern with Strategy for different workflows.
    """
    
    def __init__(self, leave_request):
        self.leave_request = leave_request
    
    @abstractmethod
    def get_approval_flow(self) -> Dict[str, str]:
        """Return the approval flow mapping for this handler."""
        pass
    
    @abstractmethod
    def get_next_approver(self, current_status: str) -> Optional[CustomUser]:
        """Get the next approver based on current status."""
        pass
    
    def can_approve(self, user: CustomUser, current_status: str) -> bool:
        """Check if user can approve at the current status."""
        flow = self.get_approval_flow()
        required_role = flow.get(current_status)
        user_role = getattr(user, 'role', None)
        
        # Admin can always approve
        if getattr(user, 'is_superuser', False) or user_role == 'admin':
            return True
        
        # Basic role check
        if user_role != required_role:
            return False
            
        # For CEO approval, ensure it's the correct CEO for the employee's affiliate
        if required_role == 'ceo':
            expected_ceo = ApprovalRoutingService.get_ceo_for_employee(self.leave_request.employee)
            return bool(expected_ceo and getattr(user, 'id', None) == getattr(expected_ceo, 'id', None))
            
        return True
    
    def get_next_status(self, current_status: str) -> str:
        """Get next status after approval."""
        flow = self.get_approval_flow()
        status_progression = {
            'pending': 'manager_approved',
            'manager_approved': 'hr_approved', 
            'hr_approved': 'approved'
        }
        return status_progression.get(current_status, 'approved')


class MerbanApprovalHandler(ApprovalHandler):
    """
    Merban approval workflow: Manager → HR → CEO (of employee's affiliate)
    Used for Merban Capital employees.
    """
    
    def get_approval_flow(self) -> Dict[str, str]:
        """Dynamic flow based on requester role.
        - Staff (default): manager -> hr -> ceo
        - Manager/HOD: hr -> ceo (skip manager)
        - HR: ceo (Merban) only (skip manager and hr)
        """
        emp = self.leave_request.employee
        role = getattr(emp, 'role', None)
        if role in ['manager', 'hod']:
            return {
                'pending': 'hr',
                'hr_approved': 'ceo'
            }
        if role == 'hr':
            return {
                'pending': 'ceo'
            }
        # Default staff flow
        return {
            'pending': 'manager',
            'manager_approved': 'hr',
            'hr_approved': 'ceo'
        }
    
    def get_next_approver(self, current_status: str) -> Optional[CustomUser]:
        if current_status == 'pending':
            emp = self.leave_request.employee
            role = getattr(emp, 'role', None)
            # Manager/HOD requests go to HR directly
            if role in ['manager', 'hod']:
                return User.objects.filter(role='hr', is_active=True).first()
            # HR requests go to Merban CEO directly
            if role == 'hr':
                # Find Merban affiliate CEO (treat MERBAN and MERBAN CAPITAL as synonyms)
                try:
                    return (
                        User.objects.filter(role__iexact='ceo', is_active=True)
                        .filter(affiliate__name__in=['MERBAN', 'MERBAN CAPITAL'])
                        .order_by('id')
                    ).first()
                except Exception:
                    # Strict: no fallback CEO
                    return None
            # Default: staff -> manager
            if hasattr(emp, 'manager') and emp.manager:
                return emp.manager
            elif hasattr(emp, 'department') and emp.department and hasattr(emp.department, 'hod'):
                return emp.department.hod
            return None
        elif current_status == 'manager_approved':
            # Any HR user can approve
            return User.objects.filter(role='hr', is_active=True).first()
        elif current_status == 'hr_approved':
            # CEO based on employee's affiliate
            return ApprovalRoutingService.get_ceo_for_employee(self.leave_request.employee)
        return None


class SDSLApprovalHandler(ApprovalHandler):
    """
    SDSL special workflow: Staff → SDSL CEO (first) → HR (final approval)
    No final CEO step - HR gives final approval after SDSL CEO.
    """
    
    def get_approval_flow(self) -> Dict[str, str]:
        """SDSL/SBL flow has no manager/HOD step: CEO -> HR (final)."""
        return {
            'pending': 'ceo',        # CEO first
            'ceo_approved': 'hr'     # HR final approval
        }
    
    def can_approve(self, user: CustomUser, current_status: str) -> bool:
        """CEO approves at pending stage for SDSL/SBL; rely on base affiliate-CEO check."""
        return super().can_approve(user, current_status)
    
    def get_next_approver(self, current_status: str) -> Optional[CustomUser]:
        if current_status == 'pending':
            # CEO based on employee's affiliate (SDSL/SBL)
            return ApprovalRoutingService.get_ceo_for_employee(self.leave_request.employee)
        elif current_status == 'ceo_approved':
            # HR for final approval
            return User.objects.filter(role='hr', is_active=True).first()
        return None
    
    def get_next_status(self, current_status: str) -> str:
        """SDSL/SBL status progression: pending -> ceo_approved -> approved (HR final)."""
        if current_status == 'pending':
            return 'ceo_approved'
        elif current_status == 'ceo_approved':
            return 'approved'
        return 'approved'


class SBLApprovalHandler(ApprovalHandler):
    """
    SBL special workflow: Staff → SBL CEO (first) → HR (final approval)
    No final CEO step - HR gives final approval after SBL CEO.
    """

    def get_approval_flow(self) -> Dict[str, str]:
        """SBL flow has no manager/HOD step: CEO -> HR (final)."""
        return {
            'pending': 'ceo',        # CEO first
            'ceo_approved': 'hr'     # HR final approval
        }

    def can_approve(self, user: CustomUser, current_status: str) -> bool:
        """CEO approves at pending stage for SBL; rely on base affiliate-CEO check."""
        return super().can_approve(user, current_status)

    def get_next_approver(self, current_status: str) -> Optional[CustomUser]:
        if current_status == 'pending':
            # CEO based on employee's affiliate (SBL)
            return ApprovalRoutingService.get_ceo_for_employee(self.leave_request.employee)
        elif current_status == 'ceo_approved':
            # HR for final approval
            return User.objects.filter(role='hr', is_active=True).first()
        return None

    def get_next_status(self, current_status: str) -> str:
        """SBL status progression: pending -> ceo_approved -> approved (HR final)."""
        if current_status == 'pending':
            return 'ceo_approved'
        elif current_status == 'ceo_approved':
            return 'approved'
        return 'approved'


class UnknownAffiliateHandler(ApprovalHandler):
    """Handler used when an employee's affiliate is missing or unrecognized.

    Strict routing policy: Requests with unknown affiliates are not routable and cannot be
    approved until the user's affiliate (or department affiliate) is corrected. All approval
    checks will fail and attempts to approve will raise a validation error upstream.
    """

    def get_approval_flow(self) -> Dict[str, str]:
        return {}

    def get_next_approver(self, current_status: str) -> Optional[CustomUser]:
        return None

    def get_next_status(self, current_status: str) -> str:
        return current_status


class ApprovalWorkflowService:
    """
    Factory service to get appropriate approval handler based on employee's affiliate.
    Implements Factory Pattern.
    """
    
    @classmethod
    def get_handler(cls, leave_request) -> ApprovalHandler:
        """Get appropriate approval handler based on employee's affiliate."""
        employee = leave_request.employee
        affiliate_name = ApprovalRoutingService.get_employee_affiliate_name(employee)
        if not affiliate_name:
            return UnknownAffiliateHandler(leave_request)
        if affiliate_name == 'SDSL':
            return SDSLApprovalHandler(leave_request)
        if affiliate_name == 'SBL':
            return SBLApprovalHandler(leave_request)
        if affiliate_name in ['MERBAN', 'MERBAN CAPITAL']:
            return MerbanApprovalHandler(leave_request)
        # Unknown affiliate: strict mode returns handler that blocks approval
        return UnknownAffiliateHandler(leave_request)
    
    @classmethod
    def can_user_approve(cls, leave_request, user: CustomUser) -> bool:
        """Check if user can approve the given leave request."""
        handler = cls.get_handler(leave_request)
        return handler.can_approve(user, leave_request.status)
    
    @classmethod
    def get_next_approver(cls, leave_request) -> Optional[CustomUser]:
        """Get next approver for the leave request."""
        handler = cls.get_handler(leave_request)
        return handler.get_next_approver(leave_request.status)
    
    @classmethod
    def approve_request(cls, leave_request, approver: CustomUser, comments: str = ""):
        """Approve request using appropriate workflow with row locking and explicit permission errors."""
        logger = logging.getLogger('leaves')
        handler = cls.get_handler(leave_request)

        if isinstance(handler, UnknownAffiliateHandler):
            raise ValidationError("Leave request cannot be approved: employee affiliate is missing or unrecognized. Fix the user's affiliate and retry.")

        with transaction.atomic():
            # Lock the row to prevent concurrent approvals
            lr = leave_request.__class__.objects.select_for_update().get(pk=leave_request.pk)

            # Re-evaluate handler against locked state
            handler = cls.get_handler(lr)

            if not handler.can_approve(approver, lr.status):
                raise PermissionDenied(f"User {getattr(approver,'email',approver)} cannot approve request in status {lr.status}")

            # Determine required role for this status
            flow = handler.get_approval_flow()
            required_role = flow.get(lr.status)
            if required_role is None:
                raise ValidationError(f"No approval mapping for status {lr.status} in {handler.__class__.__name__}")

            # Apply the appropriate stage based on required_role
            if required_role == 'manager':
                lr.manager_approve(approver, comments)
            elif required_role == 'hr':
                lr.hr_approve(approver, comments)
            elif required_role == 'ceo':
                # SDSL/SBL: CEO approval moves to ceo_approved; Merban: final approve if HR already approved
                lr.ceo_approve(approver, comments)
            else:
                # Fallback for unexpected mapping; progress using default status transition
                next_status = handler.get_next_status(lr.status)
                if next_status == 'manager_approved':
                    lr.manager_approve(approver, comments)
                elif next_status == 'hr_approved':
                    lr.hr_approve(approver, comments)
                else:
                    lr.ceo_approve(approver, comments)