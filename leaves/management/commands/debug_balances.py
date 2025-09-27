from django.core.management.base import BaseCommand
from users.models import CustomUser
from leaves.models import LeaveBalance
from leaves.serializers import LeaveBalanceSerializer
from django.utils import timezone


class Command(BaseCommand):
    help = 'Check leave balance serialization for Augustine to debug dashboard issues.'

    def handle(self, *args, **options):
        self.stdout.write('=== Leave Balance Debug Report ===')
        
        # Find Augustine
        try:
            user = CustomUser.objects.get(username='aakorfu')
            self.stdout.write(f'✅ Found user: {user.username} ({user.get_full_name()})')
        except CustomUser.DoesNotExist:
            self.stdout.write('❌ User aakorfu not found!')
            return
        
        # Get leave balances
        current_year = timezone.now().year
        balances = LeaveBalance.objects.filter(employee=user, year=current_year)
        
        self.stdout.write(f'✅ Found {balances.count()} leave balances:')
        
        for balance in balances:
            self.stdout.write(f'\n--- {balance.leave_type.name} ---')
            self.stdout.write(f'Raw data:')
            self.stdout.write(f'  - Entitled: {balance.entitled_days}')
            self.stdout.write(f'  - Used: {balance.used_days}')
            self.stdout.write(f'  - Pending: {balance.pending_days}')
            self.stdout.write(f'  - Remaining: {balance.remaining_days}')
            
            # Test serialization
            serializer = LeaveBalanceSerializer(balance)
            self.stdout.write(f'Serialized data:')
            for key, value in serializer.data.items():
                self.stdout.write(f'  - {key}: {value}')
        
        if not balances.exists():
            self.stdout.write('❌ No leave balances found!')
        
        self.stdout.write('\n=== Dashboard API Test ===')
        
        # Simulate dashboard data fetch
        user_balances = LeaveBalance.objects.filter(employee=user, year=current_year)
        serializer = LeaveBalanceSerializer(user_balances, many=True)
        
        self.stdout.write('Dashboard would receive:')
        import json
        self.stdout.write(json.dumps(serializer.data, indent=2))