from django.core.management.base import BaseCommand
from users.models import CustomUser, Department

class Command(BaseCommand):
    help = "List users with role, department, manager, active flag"

    def add_arguments(self, parser):
        parser.add_argument('--inactive', action='store_true', help='Include inactive users')

    def handle(self, *args, **options):
        qs = CustomUser.objects.all().select_related('department', 'manager')
        if not options.get('inactive'):
            qs = qs.filter(is_active=True, is_active_employee=True)
        if not qs.exists():
            self.stdout.write('No users found.')
            return
        self.stdout.write(f"Total users: {qs.count()}")
        for u in qs.order_by('username'):
            self.stdout.write(
                f"{u.username:20} role={u.role:7} emp_id={u.employee_id:8} dept={(u.department.name if u.department else '-'):<20} manager={(u.manager.username if u.manager else '-'):<15} active={u.is_active} staff_active={u.is_active_employee}"
            )
