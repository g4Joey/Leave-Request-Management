"""
Management command to update Merban Capital department names and create new departments.
Run this on your Digital Ocean production database.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import Department, Affiliate


class Command(BaseCommand):
    help = 'Update Merban Capital department names and create new departments'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting department updates for Merban Capital...'))
        
        try:
            with transaction.atomic():
                # Get Merban Capital affiliate
                try:
                    merban = Affiliate.objects.get(name='Merban Capital')
                    self.stdout.write(self.style.SUCCESS(f'Found Merban Capital affiliate (ID: {merban.id})'))
                except Affiliate.DoesNotExist:
                    self.stdout.write(self.style.ERROR('Merban Capital affiliate not found!'))
                    return
                
                # Track updates
                updated = []
                created = []
                
                # 1. Rename Accounts & Compliance → Finance & Accounts (Merban Capital)
                dept = Department.objects.filter(
                    name__iexact='Accounts & Compliance',
                    affiliate=merban
                ).first()
                if dept:
                    old_name = dept.name
                    dept.name = 'Finance & Accounts (Merban Capital)'
                    dept.save()
                    updated.append(f'{old_name} → {dept.name}')
                    self.stdout.write(self.style.SUCCESS(f'✓ Renamed: {old_name} → {dept.name}'))
                else:
                    self.stdout.write(self.style.WARNING('⚠ Accounts & Compliance not found'))
                
                # 2. Rename Government Securities → Government Securities (Merban Capital)
                dept = Department.objects.filter(
                    name__iexact='Government Securities',
                    affiliate=merban
                ).first()
                if dept:
                    old_name = dept.name
                    dept.name = 'Government Securities (Merban Capital)'
                    dept.save()
                    updated.append(f'{old_name} → {dept.name}')
                    self.stdout.write(self.style.SUCCESS(f'✓ Renamed: {old_name} → {dept.name}'))
                else:
                    self.stdout.write(self.style.WARNING('⚠ Government Securities not found'))
                
                # 3. Rename PENSIONS → Pensions & Provident Funds (Merban Capital)
                dept = Department.objects.filter(
                    name__iexact='PENSIONS',
                    affiliate=merban
                ).first()
                if dept:
                    old_name = dept.name
                    dept.name = 'Pensions & Provident Funds (Merban Capital)'
                    dept.save()
                    updated.append(f'{old_name} → {dept.name}')
                    self.stdout.write(self.style.SUCCESS(f'✓ Renamed: {old_name} → {dept.name}'))
                else:
                    self.stdout.write(self.style.WARNING('⚠ PENSIONS not found'))
                
                # 4. Rename IT → IT (Merban Capital)
                dept = Department.objects.filter(
                    name__iexact='IT',
                    affiliate=merban
                ).first()
                if dept:
                    old_name = dept.name
                    dept.name = 'IT (Merban Capital)'
                    dept.save()
                    staff_count = dept.customuser_set.count()
                    updated.append(f'{old_name} → {dept.name} ({staff_count} staff)')
                    self.stdout.write(self.style.SUCCESS(f'✓ Renamed: {old_name} → {dept.name} ({staff_count} staff)'))
                else:
                    self.stdout.write(self.style.WARNING('⚠ IT not found'))
                
                # 5. Rename IHL → Client Service/Marketing (Merban Capital)
                dept = Department.objects.filter(
                    name__iexact='IHL',
                    affiliate=merban
                ).first()
                if dept:
                    old_name = dept.name
                    dept.name = 'Client Service/Marketing (Merban Capital)'
                    dept.save()
                    updated.append(f'{old_name} → {dept.name}')
                    self.stdout.write(self.style.SUCCESS(f'✓ Renamed: {old_name} → {dept.name}'))
                else:
                    self.stdout.write(self.style.WARNING('⚠ IHL not found'))
                
                # 6. Rename Client Service → HR & Admin (Merban Capital)
                dept = Department.objects.filter(
                    name__iexact='Client Service',
                    affiliate=merban
                ).first()
                if dept:
                    old_name = dept.name
                    dept.name = 'HR & Admin (Merban Capital)'
                    dept.save()
                    staff_count = dept.customuser_set.count()
                    updated.append(f'{old_name} → {dept.name} (has HR user, {staff_count} staff)')
                    self.stdout.write(self.style.SUCCESS(f'✓ Renamed: {old_name} → {dept.name} (HR user inside, {staff_count} staff)'))
                else:
                    self.stdout.write(self.style.WARNING('⚠ Client Service not found'))
                
                # 7. Keep Executive department as is (has Benjamin Ackah)
                dept = Department.objects.filter(
                    name__icontains='Executive',
                    affiliate=merban
                ).first()
                if dept:
                    staff_count = dept.customuser_set.count()
                    self.stdout.write(self.style.SUCCESS(f'✓ Kept: {dept.name} (Benjamin Ackah, {staff_count} staff)'))
                
                # 8. Rename STOCKBROKERS → Private Wealth & Mutual Fund (Merban Capital)
                dept = Department.objects.filter(
                    name__iexact='STOCKBROKERS',
                    affiliate=merban
                ).first()
                if dept:
                    old_name = dept.name
                    dept.name = 'Private Wealth & Mutual Fund (Merban Capital)'
                    dept.save()
                    updated.append(f'{old_name} → {dept.name}')
                    self.stdout.write(self.style.SUCCESS(f'✓ Renamed: {old_name} → {dept.name}'))
                else:
                    self.stdout.write(self.style.WARNING('⚠ STOCKBROKERS not found'))
                
                # 9. Rename SDSL department (NOT the affiliate) → Corporate Finance (Merban Capital)
                # Look for department named SDSL under Merban Capital
                dept = Department.objects.filter(
                    name__iexact='SDSL',
                    affiliate=merban
                ).first()
                if dept:
                    old_name = dept.name
                    dept.name = 'Corporate Finance (Merban Capital)'
                    dept.save()
                    updated.append(f'{old_name} → {dept.name}')
                    self.stdout.write(self.style.SUCCESS(f'✓ Renamed: {old_name} → {dept.name}'))
                else:
                    self.stdout.write(self.style.WARNING('⚠ SDSL department not found under Merban Capital'))
                
                # 10. Create Audit department
                audit_dept, audit_created = Department.objects.get_or_create(
                    name='Audit (Merban Capital)',
                    affiliate=merban,
                    defaults={'manager': None}
                )
                if audit_created:
                    created.append('Audit (Merban Capital)')
                    self.stdout.write(self.style.SUCCESS('✓ Created: Audit (Merban Capital)'))
                else:
                    self.stdout.write(self.style.WARNING('⚠ Audit department already exists'))
                
                # 11. Create Compliance department
                compliance_dept, compliance_created = Department.objects.get_or_create(
                    name='Compliance (Merban Capital)',
                    affiliate=merban,
                    defaults={'manager': None}
                )
                if compliance_created:
                    created.append('Compliance (Merban Capital)')
                    self.stdout.write(self.style.SUCCESS('✓ Created: Compliance (Merban Capital)'))
                else:
                    self.stdout.write(self.style.WARNING('⚠ Compliance department already exists'))
                
                # Summary
                self.stdout.write(self.style.SUCCESS('\n' + '='*60))
                self.stdout.write(self.style.SUCCESS('SUMMARY'))
                self.stdout.write(self.style.SUCCESS('='*60))
                self.stdout.write(self.style.SUCCESS(f'Updated departments: {len(updated)}'))
                for item in updated:
                    self.stdout.write(f'  • {item}')
                self.stdout.write(self.style.SUCCESS(f'\nCreated departments: {len(created)}'))
                for item in created:
                    self.stdout.write(f'  • {item}')
                
                # List all Merban Capital departments
                self.stdout.write(self.style.SUCCESS('\n' + '='*60))
                self.stdout.write(self.style.SUCCESS('ALL MERBAN CAPITAL DEPARTMENTS'))
                self.stdout.write(self.style.SUCCESS('='*60))
                all_depts = Department.objects.filter(affiliate=merban).order_by('name')
                for dept in all_depts:
                    staff_count = dept.customuser_set.count()
                    manager_info = f', Manager: {dept.manager}' if dept.manager else ''
                    self.stdout.write(f'  • {dept.name} ({staff_count} staff{manager_info})')
                
                self.stdout.write(self.style.SUCCESS('\n✓ All changes committed successfully!'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error: {str(e)}'))
            raise
