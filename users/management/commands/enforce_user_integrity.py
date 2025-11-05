from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Affiliate
from django.db import transaction

class Command(BaseCommand):
    help = "Audit and enforce user affiliate/department integrity."

    def add_arguments(self, parser):
        parser.add_argument('--fix', action='store_true', help='Apply fixes instead of dry-run')
        parser.add_argument('--verbose', action='store_true', help='Show detailed output')

    def handle(self, *args, **options):
        User = get_user_model()
        fix = options['fix']
        verbose = options['verbose']
        issues = 0
        fixed = 0

        def vprint(*a, **k):
            if verbose:
                self.stdout.write(" ".join(str(x) for x in a))

        with transaction.atomic():
            for u in User.objects.select_related('affiliate', 'department__affiliate').all():
                before = (getattr(u.affiliate, 'name', None), getattr(u.department, 'id', None), getattr(u.manager, 'id', None))
                try:
                    # Superusers may not have an affiliate by design; skip strict checks
                    if getattr(u, 'is_superuser', False) and not u.affiliate:
                        vprint(f"Superuser {u.id} has no affiliate (allowed)")
                        continue
                    # Affiliate must exist; if missing, try infer from department
                    if not u.affiliate:
                        if u.department and u.department.affiliate:
                            u.affiliate = u.department.affiliate
                            vprint(f"User {u.id} affiliate set from department -> {u.affiliate.name}")
                        else:
                            issues += 1
                            self.stdout.write(f"MISSING AFFILIATE: user {u.id} {u.email}")
                            continue

                    aff = (u.affiliate.name or '').strip().upper()

                    if aff in ['SDSL', 'SBL']:
                        # Clear department and manager
                        if u.department_id is not None:
                            u.department = None
                        if u.manager_id is not None:
                            u.manager = None
                    elif aff in ['MERBAN', 'MERBAN CAPITAL']:
                        # Non-CEO/admin require department belonging to Merban
                        if u.role not in ['ceo', 'admin']:
                            if not u.department:
                                issues += 1
                                self.stdout.write(f"MERBAN WITHOUT DEPARTMENT: user {u.id} {u.email}")
                                continue
                            dept_aff = (getattr(getattr(u.department, 'affiliate', None), 'name', '') or '').strip().upper()
                            if dept_aff not in ['MERBAN', 'MERBAN CAPITAL']:
                                issues += 1
                                self.stdout.write(f"DEPT AFFILIATE MISMATCH: user {u.id} dept_aff={dept_aff}")
                                continue

                    # Validate via model clean (superuser case is bypassed inside clean)
                    u.clean()

                    if fix:
                        u.save()
                        after = (getattr(u.affiliate, 'name', None), getattr(u.department, 'id', None), getattr(u.manager, 'id', None))
                        if before != after:
                            fixed += 1
                except Exception as e:
                    issues += 1
                    self.stdout.write(f"ERROR user {u.id}: {e}")
                    continue

        summary = f"Integrity audit completed. Issues: {issues}. {'Fixed: ' + str(fixed) if fix else 'Run with --fix to apply changes.'}"
        self.stdout.write(summary)
