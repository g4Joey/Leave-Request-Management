from django.core.management.base import BaseCommand
from users.models import CustomUser
from leaves.models import LeaveBalance, LeaveRequest
from django.utils import timezone

class Command(BaseCommand):
    help = 'Fix production data: keep only Ato as manager, remove other managers, and ensure leave balances.'

    def handle(self, *args, **options):
        # 1. Keep only jmankoe as manager
        ato = CustomUser.objects.filter(username='jmankoe').first()
        if not ato:
            self.stdout.write(self.style.ERROR('Ato (jmankoe) not found!'))
            return
        managers = CustomUser.objects.filter(role='manager').exclude(username='jmankoe')
        for manager in managers:
            # Remove leave balances and requests if needed
            LeaveBalance.objects.filter(employee=manager).delete()
            LeaveRequest.objects.filter(employee=manager).delete()
            # Optionally, delete the user
            manager.delete()
            self.stdout.write(self.style.SUCCESS(f'Removed manager: {manager.username}'))
        self.stdout.write(self.style.SUCCESS('Only Ato remains as manager.'))

        # 2. Ensure leave balances for all active employees for current year
        current_year = timezone.now().year
        from leaves.management.commands.set_global_entitlements import set_global_entitlements
        set_global_entitlements(current_year)
        self.stdout.write(self.style.SUCCESS('Leave balances ensured for all active employees.'))
