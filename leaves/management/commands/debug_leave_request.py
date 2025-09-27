from django.core.management.base import BaseCommand
from users.models import CustomUser
from leaves.models import LeaveType, LeaveBalance, LeaveRequest
from django.utils import timezone
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Debug leave request issues by checking user data and attempting to create a test request.'

    def handle(self, *args, **options):
        self.stdout.write('=== Leave Request Debug Report ===')
        
        # Find Augustine Akorfu
        try:
            user = CustomUser.objects.get(username='aakorfu')
            self.stdout.write(f'✅ Found user: {user.username} ({user.get_full_name()})')
            self.stdout.write(f'   Role: {user.role}, Active: {user.is_active}, Department: {user.department}')
        except CustomUser.DoesNotExist:
            self.stdout.write('❌ User aakorfu not found!')
            return
        
        # Check leave types
        leave_types = LeaveType.objects.filter(is_active=True)
        self.stdout.write(f'✅ Found {leave_types.count()} active leave types:')
        for lt in leave_types:
            self.stdout.write(f'   - {lt.name} (ID: {lt.id})')
        
        if not leave_types.exists():
            self.stdout.write('❌ No active leave types found!')
            return
        
        # Check leave balances for Augustine
        current_year = timezone.now().year
        balances = LeaveBalance.objects.filter(employee=user, year=current_year)
        self.stdout.write(f'✅ Found {balances.count()} leave balances for {current_year}:')
        
        for balance in balances:
            remaining = balance.entitled_days - balance.used_days - balance.pending_days
            self.stdout.write(
                f'   - {balance.leave_type.name}: '
                f'{remaining} remaining ({balance.entitled_days} entitled, '
                f'{balance.used_days} used, {balance.pending_days} pending)'
            )
        
        if not balances.exists():
            self.stdout.write('❌ No leave balances found for current year!')
            self.stdout.write('Creating leave balances...')
            
            for leave_type in leave_types:
                balance = LeaveBalance.objects.create(
                    employee=user,
                    leave_type=leave_type,
                    year=current_year,
                    entitled_days=self._get_default_entitlement(user, leave_type),
                    used_days=0,
                    pending_days=0,
                )
                self.stdout.write(f'   Created {leave_type.name}: {balance.entitled_days} days')
        
        # Test leave request creation
        annual_leave = leave_types.filter(name__icontains='annual').first()
        if not annual_leave:
            annual_leave = leave_types.first()
        
        self.stdout.write(f'✅ Testing leave request creation with {annual_leave.name}...')
        
        # Get next Monday and Friday
        today = timezone.now().date()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7  # If today is Monday, get next Monday
        
        start_date = today + timedelta(days=days_until_monday)
        end_date = start_date + timedelta(days=4)  # Friday
        
        try:
            # Calculate working days
            working_days = 0
            current = start_date
            while current <= end_date:
                if current.weekday() < 5:  # Monday to Friday
                    working_days += 1
                current += timedelta(days=1)
            
            self.stdout.write(f'   Dates: {start_date} to {end_date} ({working_days} working days)')
            
            # Check if user has enough balance
            balance = LeaveBalance.objects.get(
                employee=user,
                leave_type=annual_leave,
                year=start_date.year
            )
            
            remaining = balance.entitled_days - balance.used_days - balance.pending_days
            self.stdout.write(f'   Balance check: {remaining} days available, {working_days} days requested')
            
            if working_days > remaining:
                self.stdout.write(f'❌ Insufficient balance! Need {working_days}, have {remaining}')
            else:
                self.stdout.write('✅ Sufficient balance available')
                
                # Try to create leave request
                leave_request = LeaveRequest(
                    employee=user,
                    leave_type=annual_leave,
                    start_date=start_date,
                    end_date=end_date,
                    reason='Debug test request',
                    status='pending'
                )
                
                # This will trigger validation
                leave_request.full_clean()
                leave_request.save()
                
                self.stdout.write(f'✅ Test leave request created successfully! ID: {leave_request.id}')
                
                # Clean up test request
                leave_request.delete()
                self.stdout.write('✅ Test request deleted')
                
        except Exception as e:
            self.stdout.write(f'❌ Leave request creation failed: {str(e)}')
            import traceback
            self.stdout.write(traceback.format_exc())
    
    def _get_default_entitlement(self, user, leave_type):
        """Calculate default entitlement based on leave type and user role."""
        if leave_type.name.lower() in ['annual', 'annual leave']:
            return getattr(user, 'annual_leave_entitlement', 25)
        elif leave_type.name.lower() in ['sick', 'sick leave']:
            return 14 if user.role in ['manager', 'admin', 'hr'] else 10
        elif leave_type.name.lower() in ['maternity', 'maternity leave']:
            return 90 if user.role in ['manager', 'admin', 'hr'] else 84
        elif leave_type.name.lower() in ['paternity', 'paternity leave']:
            return 14 if user.role in ['manager', 'admin', 'hr'] else 7
        elif leave_type.name.lower() in ['compassionate', 'compassionate leave']:
            return 5
        elif leave_type.name.lower() in ['casual', 'casual leave']:
            return 7 if user.role in ['manager', 'admin', 'hr'] else 5
        else:
            return 10