from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import Department, Affiliate, CustomUser


class Command(BaseCommand):
    help = 'Rename departments for Merban Capital affiliate and create missing ones'

    def handle(self, *args, **options):
        self.stdout.write('Starting Merban Capital department restructure...')
        
        with transaction.atomic():
            # Get Merban Capital affiliate
            merban = Affiliate.objects.filter(name__iexact='MERBAN CAPITAL').first()
            if not merban:
                self.stdout.write(self.style.ERROR('Merban Capital affiliate not found. Please create it first.'))
                return
            
            self.stdout.write(f'Found affiliate: {merban.name} (ID: {merban.id})')
            
            # Department renaming map: old_name -> new_name
            renamings = {
                'Accounts & Compliance': 'Finance & Accounts ',
                'Government Securities': 'Government Securities',
                'Pensions': 'Pensions & Provident Funds',
                'IT': 'IT',
                'IHL': 'Client Service/Marketing',
                'Client Service': 'HR & Admin',
                'Stockbrokers': 'Private Wealth & Mutual Fund',
                'SDSL': 'Corporate Finance',  # Department name, not affiliate
            }
            
            # Rename existing departments
            for old_name, new_name in renamings.items():
                dept = Department.objects.filter(name__iexact=old_name).first()
                if dept:
                    old_dept_name = dept.name
                    dept.name = new_name
                    dept.affiliate = merban
                    dept.save(update_fields=['name', 'affiliate'])
                    staff_count = CustomUser.objects.filter(department=dept, is_active=True).count()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Renamed "{old_dept_name}" → "{new_name}" '
                            f'(ID: {dept.id}, {staff_count} staff, HOD: {dept.hod.get_full_name() if dept.hod else "None"})'
                        )
                    )
                else:
                    self.stdout.write(self.style.WARNING(f'⚠ Department "{old_name}" not found, skipping.'))
            
            # Create new departments if they don't exist
            new_departments = [
                ('Audit (Merban Capital)', 'Internal audit and controls'),
                ('Compliance (Merban Capital)', 'Regulatory compliance and risk'),
            ]
            
            for dept_name, dept_desc in new_departments:
                existing = Department.objects.filter(name__iexact=dept_name).first()
                if existing:
                    self.stdout.write(f'Department "{dept_name}" already exists (ID: {existing.id})')
                    # Ensure it's linked to Merban
                    if existing.affiliate != merban:
                        existing.affiliate = merban
                        existing.save(update_fields=['affiliate'])
                        self.stdout.write(self.style.SUCCESS(f'✓ Linked "{dept_name}" to Merban Capital'))
                else:
                    dept = Department.objects.create(
                        name=dept_name,
                        description=dept_desc,
                        affiliate=merban
                    )
                    self.stdout.write(self.style.SUCCESS(f'✓ Created new department: "{dept_name}" (ID: {dept.id})'))
            
            # Verify HR user is in HR & Admin department
            hr_admin_dept = Department.objects.filter(name__icontains='HR & Admin').first()
            if hr_admin_dept:
                hr_users = CustomUser.objects.filter(role='hr', is_active=True)
                for hr_user in hr_users:
                    if hr_user.department != hr_admin_dept:
                        hr_user.department = hr_admin_dept
                        hr_user.save(update_fields=['department'])
                        self.stdout.write(f'✓ Moved HR user {hr_user.get_full_name()} to "{hr_admin_dept.name}"')
            
            # Summary report
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.SUCCESS('Merban Capital Departments Summary:'))
            self.stdout.write('='*60)
            
            merban_depts = Department.objects.filter(affiliate=merban).order_by('name')
            for dept in merban_depts:
                staff_count = CustomUser.objects.filter(department=dept, is_active=True).count()
                hod_info = dept.hod.get_full_name() if dept.hod else 'Not assigned'
                self.stdout.write(f'  • {dept.name}')
                self.stdout.write(f'    - Staff: {staff_count}')
                self.stdout.write(f'    - HOD: {hod_info}')
                self.stdout.write(f'    - ID: {dept.id}')
                self.stdout.write('')
            
        self.stdout.write(self.style.SUCCESS('\n✓ Department restructure completed successfully!'))
