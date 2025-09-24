from django.core.management.base import BaseCommand
from leaves.models import LeaveType


class Command(BaseCommand):
    help = 'Create default leave types if they do not exist (idempotent).'

    DEFAULT_TYPES = [
        ('Annual', 'Annual leave entitlement'),
        ('Sick', 'Sick leave; may require medical certificate'),
        ('Maternity', 'Maternity leave'),
        ('Paternity', 'Paternity leave'),
        ('Compassionate', 'Compassionate leave'),
        ('Casual', 'Casual leave'),
    ]

    def handle(self, *args, **options):
        self.stdout.write('Ensuring default leave types exist...')
        created = 0
        for name, desc in self.DEFAULT_TYPES:
            lt, was_created = LeaveType.objects.get_or_create(
                name=name,
                defaults={
                    'description': desc,
                    'max_days_per_request': 30,
                    'requires_medical_certificate': name.lower() == 'sick',
                    'is_active': True,
                },
            )
            if not was_created:
                # keep description updated idempotently
                if lt.description != desc:
                    LeaveType.objects.filter(pk=lt.pk).update(description=desc)
            else:
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Default leave types ensured (created {created}).'))
