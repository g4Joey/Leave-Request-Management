"""
Production-ready management command to create leave balances and fix dashboard data.
This will run as a Django management command to ensure proper database connection.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from leaves.models import LeaveBalance, LeaveType, LeaveRequest
from users.models import CustomUser


class Command(BaseCommand):
    help = 'Create leave balances and sample data for dashboard display'

    def handle(self, *args, **options):
        self.stdout.write("=== DASHBOARD DATA FIX ===")
        
        current_year = timezone.now().year
        self.stdout.write(f"Working with year: {current_year}")
        
        # Get all active employees
        users = CustomUser.objects.filter(is_active=True, is_active_employee=True)
        self.stdout.write(f"Found {users.count()} active employees")
        
        # Get all active leave types
        leave_types = LeaveType.objects.filter(is_active=True)
        self.stdout.write(f"Found {leave_types.count()} leave types")
        
        if not leave_types.exists():
            self.stdout.write("No leave types found - this is the problem!")
            return
        
        # Default entitlements for common leave types
        default_entitlements = {
            'Annual Leave': 21,
            'Sick Leave': 10,
            'Casual Leave': 5,
            'Maternity Leave': 90,
            'Paternity Leave': 10,
            'Study Leave': 5
        }
        
        # Create leave balances for all users
        created_count = 0
        updated_count = 0
        
        for user in users:
            self.stdout.write(f"Processing user: {user.username}")
            for leave_type in leave_types:
                # Use default entitlement based on leave type name, fallback to 21
                entitled_days = default_entitlements.get(leave_type.name, 21)
                
                balance, created = LeaveBalance.objects.get_or_create(
                    employee=user,
                    leave_type=leave_type,
                    year=current_year,
                    defaults={
                        'entitled_days': entitled_days,
                        'used_days': 0,
                        'pending_days': 0,
                        'remaining_days': entitled_days
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f"  Created balance: {leave_type.name} = {entitled_days} days")
                else:
                    # Update existing balance if needed
                    if balance.entitled_days != entitled_days:
                        balance.entitled_days = entitled_days
                        balance.save()
                        updated_count += 1
                        self.stdout.write(f"  Updated balance: {leave_type.name} = {entitled_days} days")
        
        self.stdout.write(f"Created {created_count} new leave balances")
        self.stdout.write(f"Updated {updated_count} existing leave balances")
        
        # Create a sample leave request if none exist
        recent_requests = LeaveRequest.objects.filter(
            created_at__year=current_year
        ).count()
        
        if recent_requests == 0 and users.exists():
            self.stdout.write("Creating sample leave request...")
            sample_user = users.first()
            sample_leave_type = leave_types.first()
            
            if sample_leave_type and sample_user:
                LeaveRequest.objects.create(
                    employee=sample_user,
                    leave_type=sample_leave_type,
                    start_date=timezone.now().date(),
                    end_date=timezone.now().date() + timezone.timedelta(days=1),
                    days_requested=2,
                    reason="Sample leave request for testing dashboard",
                    status='pending'
                )
                self.stdout.write("Created sample leave request")
        
        # Final verification
        total_balances = LeaveBalance.objects.filter(year=current_year).count()
        total_requests = LeaveRequest.objects.filter(created_at__year=current_year).count()
        
        self.stdout.write(f"\n=== FINAL STATUS ===")
        self.stdout.write(f"Total leave balances for {current_year}: {total_balances}")
        self.stdout.write(f"Total leave requests for {current_year}: {total_requests}")
        
        # Test the API endpoint
        from leaves.views import LeaveBalanceViewSet
        from unittest.mock import Mock
        
        if users.exists():
            test_user = users.first()
            request = Mock()
            request.user = test_user
            viewset = LeaveBalanceViewSet()
            viewset.request = request
            try:
                response = viewset.current_year_full(request)
                self.stdout.write(f"API test for {test_user.username}: {len(response.data)} balances returned")
                if response.data:
                    self.stdout.write(f"Sample balance: {response.data[0]}")
            except Exception as e:
                self.stdout.write(f"API test failed: {e}")
        
        self.stdout.write(self.style.SUCCESS('Dashboard data fix completed successfully!'))