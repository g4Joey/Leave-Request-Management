"""
Management command to assign CEOs to their respective affiliates as individual entities
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import CustomUser, Affiliate


class Command(BaseCommand):
    help = 'Assign CEOs to their respective affiliates as individual entities'

    def handle(self, *args, **options):
        self.stdout.write('Assigning CEOs to their respective affiliates...')
        
        with transaction.atomic():
            # Ensure affiliates exist
            merban, _ = Affiliate.objects.get_or_create(
                name='MERBAN CAPITAL', 
                defaults={'description': 'Merban Capital affiliate'}
            )
            sdsl, _ = Affiliate.objects.get_or_create(
                name='SDSL', 
                defaults={'description': 'SDSL affiliate'}
            )
            sbl, _ = Affiliate.objects.get_or_create(
                name='SBL', 
                defaults={'description': 'SBL affiliate'}
            )
            
            # CEO assignments
            ceo_assignments = [
                {
                    'email': 'ceo@umbcapital.com',
                    'affiliate': merban,
                    'name': 'Benjamin Ackah',
                    'first_name': 'Benjamin',
                    'last_name': 'Ackah'
                },
                {
                    'email': 'sdslceo@umbcapital.com', 
                    'affiliate': sdsl,
                    'name': 'Kofi Ameyaw',
                    'first_name': 'Kofi',
                    'last_name': 'Ameyaw'
                },
                {
                    'email': 'sblceo@umbcapital.com',
                    'affiliate': sbl, 
                    'name': 'Winslow Sackey',
                    'first_name': 'Winslow',
                    'last_name': 'Sackey'
                }
            ]
            
            for assignment in ceo_assignments:
                email = assignment['email']
                affiliate = assignment['affiliate']
                
                # Find or create CEO user
                user = CustomUser.objects.filter(email=email).first()
                if user:
                    # Update existing user
                    updates = {
                        'first_name': assignment['first_name'],
                        'last_name': assignment['last_name'],
                        'role': 'ceo',
                        'department': None,  # CEOs are individual entities
                        'is_staff': True,
                        'annual_leave_entitlement': 30,
                        'is_active_employee': True
                    }
                    
                    for field, value in updates.items():
                        setattr(user, field, value)
                    user.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Updated CEO: {assignment['name']} <{email}> → {affiliate.name}"
                        )
                    )
                else:
                    # Create new CEO user
                    user = CustomUser.objects.create_user(
                        username=email.split('@')[0],
                        email=email,
                        first_name=assignment['first_name'],
                        last_name=assignment['last_name'],
                        password='ChangeMe123!',
                        role='ceo',
                        department=None,  # CEOs are individual entities
                        is_staff=True,
                        annual_leave_entitlement=30,
                        is_active_employee=True
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Created CEO: {assignment['name']} <{email}> → {affiliate.name}"
                        )
                    )
            
            # Verify CEO assignments  
            self.stdout.write('\nCEO Summary:')
            ceo_emails = ['ceo@umbcapital.com', 'sdslceo@umbcapital.com', 'sblceo@umbcapital.com']
            affiliate_map = {
                'ceo@umbcapital.com': merban,
                'sdslceo@umbcapital.com': sdsl, 
                'sblceo@umbcapital.com': sbl
            }
            
            for email, affiliate in affiliate_map.items():
                ceo = CustomUser.objects.filter(email=email, role='ceo').first()
                if ceo:
                    self.stdout.write(f"  {affiliate.name}: {ceo.get_full_name()} <{ceo.email}>")
                else:
                    self.stdout.write(f"  {affiliate.name}: No CEO found")
        
        self.stdout.write(self.style.SUCCESS('CEO affiliate assignments complete!'))