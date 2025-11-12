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
        """
        Determine the appropriate CEO for an employee based on affiliate.

        Rules (case-insensitive):
        - Merban Capital: employees (including those in any Merban department) → Merban CEO
        - SDSL: employees → SDSL CEO
        - SBL: employees → SBL CEO
        - Default/No affiliate → default CEO (first active CEO)

        CEOs are attached to Affiliates (not departments). Only Merban uses departments.
        """
        logger = logging.getLogger('leaves')

        if not employee:
            return cls._get_default_ceo()

        affiliate = getattr(employee, 'affiliate', None)

        # Merban-only department override: if no user.affiliate, but department.affiliate is Merban, use that
        try:
            if not affiliate and getattr(employee, 'department', None) and getattr(employee.department, 'affiliate', None):
                dep_aff = employee.department.affiliate
                name = (getattr(dep_aff, 'name', '') or '').strip().lower()
                if name in ('merban capital', 'merban'):
                    affiliate = dep_aff
        except Exception as e:
            logger.exception("Failed to evaluate department affiliate override for employee %s: %s", getattr(employee, 'id', None), e)

        if not affiliate:
            return cls._get_default_ceo()

        # CEOs are looked up strictly by their affiliate
        try:
            ceo = (
                User.objects.filter(role__iexact='ceo', is_active=True)
                .filter(affiliate=affiliate)
                .first()
            )
            return ceo or cls._get_default_ceo()
        except Exception as e:
            logger.exception("Failed to determine CEO for employee %s: %s", getattr(employee, 'id', None), e)
            return cls._get_default_ceo()
    
    @classmethod
    def _get_default_ceo(cls) -> Optional[CustomUser]:
        """Fallback CEO: any active CEO user (first)."""
        return User.objects.filter(role='ceo', is_active=True).first()
    
    @classmethod
    def get_employee_affiliate_name(cls, employee: CustomUser) -> str:
        """Get the normalized affiliate name for an employee, preferring user.affiliate over department.affiliate.

        Rationale:
        - Every staff has an affiliate, but not every staff has a department.
        - Prefer employee.affiliate if set.
        - Fallback to department.affiliate only if user.affiliate is missing (e.g., legacy Merban records).
        - Returns uppercase name (e.g., 'SDSL', 'SBL', 'MERBAN CAPITAL') or 'DEFAULT' if not found.
        """
        def _norm(name: Optional[str]) -> Optional[str]:
            return (name or '').strip().upper() or None

        if not employee:
            return 'DEFAULT'

        # 1) Prefer direct user affiliate
        user_aff = getattr(employee, 'affiliate', None)
        if user_aff and getattr(user_aff, 'name', None):
            return _norm(user_aff.name) or 'DEFAULT'

        # 2) Fallback to department affiliate (legacy Merban-style data)
        dep = getattr(employee, 'department', None)
        dep_aff = getattr(dep, 'affiliate', None) if dep else None
        if dep_aff and getattr(dep_aff, 'name', None):
            return _norm(dep_aff.name) or 'DEFAULT'

        return 'DEFAULT'


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
        
        # For admin, check if this status has a valid next stage and treat admin as that role
        if getattr(user, 'is_superuser', False) or user_role == 'admin':
            # Admin must still follow the flow - only approve if this status has a next stage
            if current_status not in flow:
                return False
            # Admin acts as the required role for this stage
            required_role = flow.get(current_status)
            if not required_role:
                return False
            # For CEO stage, admin must still match affiliate (treated as CEO check)
            if required_role == 'ceo':
                expected_ceo = ApprovalRoutingService.get_ceo_for_employee(self.leave_request.employee)
                # Admin can approve as CEO only if they match the affiliate CEO or are superuser
                if not getattr(user, 'is_superuser', False):
                    return False  # Regular admin cannot act as CEO
            # For other stages, admin can approve
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
    """Merban Capital workflow: Manager → HR → CEO.

    Special cases:
    - Manager/HOD requester: HR → CEO (skip manager stage)
    - HR requester: CEO only (skip manager and HR stages, CEO is final)
    
    Note: Merban CEO does not request leave (no access to leave request page).
    """
    
    def get_approval_flow(self) -> Dict[str, str]:
        """Dynamic flow based on requester role.
        - Staff (default): manager -> hr -> ceo
        - Manager/HOD: hr -> ceo (skip manager)
        - HR: ceo only (skip manager and hr, CEO is final for HR requests)
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
            # HR requests go to Merban CEO directly (CEO is final for HR requests)
            if role == 'hr':
                # Route HR requests to the CEO of the employee's affiliate
                return ApprovalRoutingService.get_ceo_for_employee(emp)
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
    """SDSL workflow: CEO → HR final.

    Staff (including managers/HODs) start at CEO stage because
    SDSL does not use departmental manager approvals in the same way as Merban.
    
    Special case:
    - CEO requester: HR only (skip CEO stage)
    
    Status path: pending → ceo_approved → approved.
    """
    
    def get_approval_flow(self) -> Dict[str, str]:
        """Dynamic flow based on requester role.
        - Staff/manager/HOD (default): ceo -> hr
        - CEO: hr only (skip CEO)
        """
        emp = self.leave_request.employee
        role = getattr(emp, 'role', None)
        if role == 'ceo':
            return {
                'pending': 'hr'
            }
        # Default flow: CEO first, then HR
        return {
            'pending': 'ceo',        # CEO first
            'ceo_approved': 'hr'     # HR final approval
        }
    
    def can_approve(self, user: CustomUser, current_status: str) -> bool:
        """CEO approves at pending stage for SDSL/SBL; rely on base affiliate-CEO check."""
        return super().can_approve(user, current_status)
    
    def get_next_approver(self, current_status: str) -> Optional[CustomUser]:
        emp = self.leave_request.employee
        role = getattr(emp, 'role', None)
        
        if current_status == 'pending':
            # CEO requests go directly to HR (skip CEO stage)
            if role == 'ceo':
                return User.objects.filter(role='hr', is_active=True).first()
            # Default: CEO based on employee's affiliate (SDSL)
            return ApprovalRoutingService.get_ceo_for_employee(self.leave_request.employee)
        elif current_status == 'ceo_approved':
            # HR for final approval
            return User.objects.filter(role='hr', is_active=True).first()
        return None
    
    def get_next_status(self, current_status: str) -> str:
        """Status progression: pending -> ceo_approved -> approved (HR final)."""
        if current_status == 'pending':
            return 'ceo_approved'
        elif current_status == 'ceo_approved':
            return 'approved'
        return 'approved'


class SBLApprovalHandler(ApprovalHandler):
    """SBL workflow: CEO → HR final (mirrors SDSL requirements).

    Special case:
    - CEO requester: HR only (skip CEO stage)
    
    Status path: pending → ceo_approved → approved.
    """

    def get_approval_flow(self) -> Dict[str, str]:
        """Dynamic flow based on requester role.
        - Staff/manager/HOD (default): ceo -> hr
        - CEO: hr only (skip CEO)
        """
        emp = self.leave_request.employee
        role = getattr(emp, 'role', None)
        if role == 'ceo':
            return {
                'pending': 'hr'
            }
        # Default flow: CEO first, then HR
        return {
            'pending': 'ceo',
            'ceo_approved': 'hr'
        }

    def get_next_approver(self, current_status: str) -> Optional[CustomUser]:
        emp = self.leave_request.employee
        role = getattr(emp, 'role', None)
        
        if current_status == 'pending':
            # CEO requests go directly to HR (skip CEO stage)
            if role == 'ceo':
                return User.objects.filter(role='hr', is_active=True).first()
            # Default: CEO based on employee's affiliate
            return ApprovalRoutingService.get_ceo_for_employee(self.leave_request.employee)
        elif current_status == 'ceo_approved':
            return User.objects.filter(role='hr', is_active=True).first()
        return None

    def get_next_status(self, current_status: str) -> str:
        if current_status == 'pending':
            return 'ceo_approved'
        elif current_status == 'ceo_approved':
            return 'approved'
        return 'approved'


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
        
        if affiliate_name == 'SDSL':
            return SDSLApprovalHandler(leave_request)
        if affiliate_name == 'SBL':
            return SBLApprovalHandler(leave_request)
        # Default & Merban: Merban workflow
        return MerbanApprovalHandler(leave_request)
    
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