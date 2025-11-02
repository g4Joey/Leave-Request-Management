"""
Leave management services implementing business logic with OOP patterns.

Uses Strategy Pattern and Inheritance for different approval workflows.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from django.contrib.auth import get_user_model
from users.models import Affiliate, CustomUser


User = get_user_model()


class ApprovalRoutingService:
    """
    Encapsulates CEO routing logic based on employee's department affiliate.
    """
    
    @classmethod
    def get_ceo_for_employee(cls, employee: CustomUser) -> Optional[CustomUser]:
        """
        Determine the appropriate CEO for an employee based on their department's affiliate.
        
        Rules:
        - Merban Capital departments → Benjamin Ackah (merban CEO)  
        - SDSL departments → Kofi Ameyaw (SDSL CEO)
        - SBL departments → Winslow Sackey (SBL CEO)
        - Default/No affiliate → Benjamin Ackah
        """
        if not employee:
            return cls._get_default_ceo()
        # Prefer department affiliate when present; otherwise fall back to user's own affiliate
        affiliate = None
        if hasattr(employee, 'department') and employee.department:
            affiliate = getattr(employee.department, 'affiliate', None)
        if not affiliate and hasattr(employee, 'affiliate'):
            affiliate = getattr(employee, 'affiliate', None)

        if not affiliate:
            return cls._get_default_ceo()

        # Prefer dynamic lookup: a user with role 'ceo' whose department belongs to this affiliate or whose own affiliate matches
        try:
            ceo = (
                User.objects.filter(role='ceo', is_active=True)
                .filter(models.Q(department__affiliate=affiliate) | models.Q(affiliate=affiliate))
                .first()
            )
            return ceo or cls._get_default_ceo()
        except Exception:
            return cls._get_default_ceo()
    
    @classmethod
    def _get_default_ceo(cls) -> Optional[CustomUser]:
        """Fallback CEO: any active CEO user (first)."""
        return User.objects.filter(role='ceo', is_active=True).first()
    
    @classmethod
    def get_employee_affiliate_name(cls, employee: CustomUser) -> str:
        """Get the affiliate name for an employee, or 'DEFAULT' if none."""
        if employee:
            if (
                hasattr(employee, 'department') and employee.department and 
                hasattr(employee.department, 'affiliate') and employee.department.affiliate
            ):
                return employee.department.affiliate.name
            # Fallback to user's affiliate when no department is assigned (SDSL/SBL individual users)
            if hasattr(employee, 'affiliate') and getattr(employee, 'affiliate', None):
                return employee.affiliate.name
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
        
        # Admin can always approve
        if getattr(user, 'is_superuser', False) or user_role == 'admin':
            return True
        
        # Basic role check
        if user_role != required_role:
            return False
            
        # For CEO approval, ensure it's the correct CEO for the employee's affiliate
        if required_role == 'ceo':
            expected_ceo = ApprovalRoutingService.get_ceo_for_employee(self.leave_request.employee)
            return user == expected_ceo
            
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


class StandardApprovalHandler(ApprovalHandler):
    """
    Standard approval workflow: Manager → HR → CEO (of employee's affiliate)
    Used for Merban Capital and SBL employees.
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
                # Find Merban affiliate CEO
                try:
                    from users.models import Affiliate
                    merban = Affiliate.objects.filter(name__iexact='MERBAN CAPITAL').first()
                    if merban:
                        return User.objects.filter(role='ceo', is_active=True, department__affiliate=merban).first()
                except Exception:
                    pass
                return ApprovalRoutingService._get_default_ceo()
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
    SDSL special workflow: Manager → SDSL CEO (Kofi) → HR (final approval)
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
        
        if affiliate_name in ['SDSL', 'SBL']:
            return SDSLApprovalHandler(leave_request)
        else:
            # Standard workflow for Merban Capital, SBL, and others
            return StandardApprovalHandler(leave_request)
    
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
        """Approve request using appropriate workflow."""
        handler = cls.get_handler(leave_request)
        
        if not handler.can_approve(approver, leave_request.status):
            raise ValueError(f"User {approver} cannot approve request in status {leave_request.status}")
        
        # Determine required role for this status
        flow = handler.get_approval_flow()
        required_role = flow.get(leave_request.status)

        # Apply the appropriate stage based on required_role
        if required_role == 'manager':
            leave_request.manager_approve(approver, comments)
        elif required_role == 'hr':
            leave_request.hr_approve(approver, comments)
        elif required_role == 'ceo':
            # SDSL/SBL: CEO approval moves to ceo_approved; Merban: final approve if HR already approved
            leave_request.ceo_approve(approver, comments)
        else:
            # Fallback for unexpected mapping; progress using default status transition
            next_status = handler.get_next_status(leave_request.status)
            if next_status == 'manager_approved':
                leave_request.manager_approve(approver, comments)
            elif next_status == 'hr_approved':
                leave_request.hr_approve(approver, comments)
            else:
                leave_request.ceo_approve(approver, comments)