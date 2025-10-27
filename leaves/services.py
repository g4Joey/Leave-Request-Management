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
        if not employee or not hasattr(employee, 'department') or not employee.department:
            return cls._get_default_ceo()
        
        affiliate = getattr(employee.department, 'affiliate', None)
        if not affiliate:
            return cls._get_default_ceo()
        
        # Map affiliate to CEO
        affiliate_ceo_map = {
            'MERBAN CAPITAL': 'ceo@company.com',  # Benjamin Ackah
            'SDSL': 'sdslceo@umbcapital.com',     # Kofi Ameyaw  
            'SBL': 'sblceo@umbcapital.com',       # Winslow Sackey
        }
        
        ceo_email = affiliate_ceo_map.get(affiliate.name)
        if ceo_email:
            try:
                return User.objects.get(email=ceo_email, role='ceo', is_active=True)
            except User.DoesNotExist:
                pass
        
        return cls._get_default_ceo()
    
    @classmethod
    def _get_default_ceo(cls) -> Optional[CustomUser]:
        """Get Benjamin Ackah as the default CEO."""
        try:
            return User.objects.get(email='ceo@company.com', role='ceo', is_active=True)
        except User.DoesNotExist:
            # Fallback to any CEO
            return User.objects.filter(role='ceo', is_active=True).first()
    
    @classmethod
    def get_employee_affiliate_name(cls, employee: CustomUser) -> str:
        """Get the affiliate name for an employee, or 'DEFAULT' if none."""
        if (employee and hasattr(employee, 'department') and 
            employee.department and hasattr(employee.department, 'affiliate') and
            employee.department.affiliate):
            return employee.department.affiliate.name
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
        if required_role == 'ceo' and current_status == 'hr_approved':
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
        return {
            'pending': 'manager',
            'manager_approved': 'hr',
            'hr_approved': 'ceo'
        }
    
    def get_next_approver(self, current_status: str) -> Optional[CustomUser]:
        if current_status == 'pending':
            # Get manager from department or direct manager
            emp = self.leave_request.employee
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
        return {
            'pending': 'manager',
            'manager_approved': 'ceo',  # SDSL CEO approves after manager
            'hr_approved': 'hr'         # HR gives final approval
        }
    
    def can_approve(self, user: CustomUser, current_status: str) -> bool:
        """Override: SDSL CEO approves at manager_approved stage."""
        flow = self.get_approval_flow()
        required_role = flow.get(current_status)
        user_role = getattr(user, 'role', None)
        
        # Admin can always approve
        if getattr(user, 'is_superuser', False) or user_role == 'admin':
            return True
        
        # Basic role check
        if user_role != required_role:
            return False
            
        # For SDSL CEO approval at manager_approved stage
        if required_role == 'ceo' and current_status == 'manager_approved':
            # Must be SDSL CEO (Kofi Ameyaw)
            try:
                expected_ceo = User.objects.get(email='sdslceo@umbcapital.com', role='ceo', is_active=True)
                return user == expected_ceo
            except User.DoesNotExist:
                return False
                
        return True
    
    def get_next_approver(self, current_status: str) -> Optional[CustomUser]:
        if current_status == 'pending':
            # Get manager
            emp = self.leave_request.employee
            if hasattr(emp, 'manager') and emp.manager:
                return emp.manager
            elif hasattr(emp, 'department') and emp.department and hasattr(emp.department, 'hod'):
                return emp.department.hod
            return None
        elif current_status == 'manager_approved':
            # SDSL CEO (Kofi Ameyaw)
            try:
                return User.objects.get(email='sdslceo@umbcapital.com', role='ceo', is_active=True)
            except User.DoesNotExist:
                return None
        elif current_status == 'hr_approved':
            # HR for final approval  
            return User.objects.filter(role='hr', is_active=True).first()
        return None
    
    def get_next_status(self, current_status: str) -> str:
        """Override: SDSL has different status progression."""
        if current_status == 'pending':
            return 'manager_approved'
        elif current_status == 'manager_approved':
            return 'hr_approved'  # CEO approval moves to HR stage
        elif current_status == 'hr_approved':
            return 'approved'     # HR gives final approval
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
        
        # Get next status
        next_status = handler.get_next_status(leave_request.status)
        
        # Apply approval based on current status
        if leave_request.status == 'pending':
            leave_request.manager_approve(approver, comments)
        elif leave_request.status == 'manager_approved':
            if isinstance(handler, SDSLApprovalHandler):
                # For SDSL: this is CEO approval, but we store in hr_approved
                leave_request.hr_approve(approver, comments)
            else:
                # Standard: HR approval
                leave_request.hr_approve(approver, comments)
        elif leave_request.status == 'hr_approved':
            if isinstance(handler, SDSLApprovalHandler):
                # For SDSL: HR gives final approval
                leave_request.ceo_approve(approver, comments)
            else:
                # Standard: CEO gives final approval
                leave_request.ceo_approve(approver, comments)