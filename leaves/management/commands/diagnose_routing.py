import sys
from typing import List
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from users.models import CustomUser
from leaves.models import LeaveRequest
from leaves.services import ApprovalRoutingService, ApprovalWorkflowService


class Command(BaseCommand):
    help = "Diagnose approval routing for specified users and optionally fix affiliate/department/manager mismatches."

    def add_arguments(self, parser):
        parser.add_argument(
            '--queries', nargs='+', required=True,
            help='One or more substrings to match users by email/first/last/username'
        )
        parser.add_argument(
            '--affiliates', nargs='*', default=[],
            help='Optional affiliate names (e.g., SDSL SBL) to summarize staff and pending requests'
        )
        parser.add_argument(
            '--fix', action='store_true', default=False,
            help='Apply safe fixes: set affiliate for SDSL/SBL users when missing; clear department/manager for SDSL/SBL'
        )
        parser.add_argument(
            '--dry-run', action='store_true', default=False,
            help='Show what would be changed without applying (implies no write)'
        )
        parser.add_argument(
            '--verbose', action='store_true', default=False,
            help='Print more details for each matched user and request'
        )

    def _find_users(self, q: str) -> List[CustomUser]:
        filters = Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q)
        return list(CustomUser.objects.filter(filters, is_active=True).order_by('id').distinct())

    def handle(self, *args, **options):
        queries: List[str] = options['queries']
        affiliates: List[str] = [a.strip().upper() for a in (options.get('affiliates') or []) if a]
        do_fix: bool = bool(options['fix']) and not bool(options['dry_run'])
        dry_run: bool = bool(options['dry_run'])
        verbose: bool = bool(options['verbose'])

        self.stdout.write(self.style.MIGRATE_HEADING('== Diagnose approval routing =='))
        self.stdout.write(f"When: {timezone.now().isoformat(timespec='seconds')}  Fix: {do_fix}  Dry-run: {dry_run}\n")

        total_matched = 0
        for key in queries:
            users = self._find_users(key)
            self.stdout.write(self.style.HTTP_INFO(f"-- Query '{key}' matched {len(users)} user(s)"))
            total_matched += len(users)

            for u in users:
                aff = getattr(getattr(u, 'affiliate', None), 'name', None)
                dept = getattr(getattr(u, 'department', None), 'name', None)
                mgr_email = getattr(getattr(u, 'manager', None), 'email', None)
                self.stdout.write(
                    f"  user id={u.id} email={u.email} role={u.role} affiliate={aff} dept={dept} manager={mgr_email}"
                )

                # Diagnose affiliate consistency for SDSL/SBL users
                intended_aff = None
                if aff:
                    name_upper = aff.strip().upper()
                    if name_upper in ['SDSL', 'SBL']:
                        intended_aff = name_upper
                elif dept and getattr(getattr(u, 'department', None), 'affiliate', None):
                    d_aff = u.department.affiliate.name.strip().upper()
                    if d_aff in ['SDSL', 'SBL']:
                        intended_aff = d_aff

                planned_changes = []
                if intended_aff in ['SDSL', 'SBL']:
                    # For SDSL/SBL, ensure user.affiliate is set and department/manager are cleared
                    if getattr(u, 'affiliate', None) is None and getattr(getattr(u, 'department', None), 'affiliate', None):
                        # Set user.affiliate to department's affiliate
                        planned_changes.append('set affiliate from department')
                        if do_fix:
                            u.affiliate = u.department.affiliate
                    # Enforce no department/manager for SDSL/SBL staff (non-CEO/HR/Admin)
                    if u.role not in ['ceo', 'hr', 'admin']:
                        if getattr(u, 'department', None) is not None:
                            planned_changes.append('clear department')
                            if do_fix:
                                u.department = None
                        if getattr(u, 'manager', None) is not None:
                            planned_changes.append('clear manager')
                            if do_fix:
                                u.manager = None
                
                if planned_changes:
                    self.stdout.write(f"    planned user fixes: {', '.join(planned_changes)}")
                    if do_fix:
                        u.save(update_fields=['affiliate', 'department', 'manager'])
                        self.stdout.write(self.style.SUCCESS("    applied user fixes"))

                # Latest LeaveRequest
                lr = LeaveRequest.objects.filter(employee=u).order_by('-created_at').first()
                if not lr:
                    self.stdout.write("    no leave requests found")
                    continue

                emp_aff = ApprovalRoutingService.get_employee_affiliate_name(u)
                ceo = ApprovalRoutingService.get_ceo_for_employee(u)
                handler = ApprovalWorkflowService.get_handler(lr)
                next_appr = ApprovalWorkflowService.get_next_approver(lr)
                self.stdout.write(
                    f"    latest lr id={lr.id} status={lr.status} emp_aff='{emp_aff}' ceo_email={getattr(ceo,'email',None)} handler={handler.__class__.__name__}"
                )
                if verbose:
                    self.stdout.write(f"    next approver: {getattr(next_appr, 'email', None)}")

                # Why would admin see it? Check who can approve now under various roles
                admin_users = list(CustomUser.objects.filter(Q(is_superuser=True) | Q(role='admin'), is_active=True)[:1])
                ceo_users = list(CustomUser.objects.filter(role='ceo', is_active=True))
                hr_users = list(CustomUser.objects.filter(role='hr', is_active=True))

                def can_any(users):
                    for x in users:
                        try:
                            if ApprovalWorkflowService.can_user_approve(lr, x):
                                return x
                        except Exception:
                            continue
                    return None

                admin_can = can_any(admin_users)
                ceo_can = can_any([c for c in ceo_users if getattr(c, 'affiliate_id', None) == getattr(getattr(u, 'affiliate', None), 'id', None)]) or can_any(ceo_users)
                hr_can = can_any(hr_users)

                self.stdout.write(f"    can_admin_approve_now={bool(admin_can)} can_ceo_approve_now={bool(ceo_can)} can_hr_approve_now={bool(hr_can)}")

                # Flag mismatch causes
                causes = []
                if not getattr(u, 'affiliate', None) and not getattr(getattr(u, 'department', None), 'affiliate', None):
                    causes.append('employee has no affiliate (direct or via department)')
                if intended_aff in ['SDSL', 'SBL'] and lr.status == 'pending' and admin_can and not ceo_can:
                    causes.append('SDSL/SBL pending but CEO not matched by affiliate; admin sees by default manager queue')
                if getattr(u, 'department', None) is not None and intended_aff in ['SDSL', 'SBL']:
                    causes.append('SDSL/SBL employee should not have a department; resets route to CEO-first')
                if getattr(u, 'manager', None) is not None and intended_aff in ['SDSL', 'SBL']:
                    causes.append('SDSL/SBL employee should not have a manager; prevents manager queue leakage')

                if causes:
                    for c in causes:
                        self.stdout.write(self.style.WARNING(f"    cause: {c}"))

        if total_matched == 0:
            self.stdout.write(self.style.WARNING('No users matched the provided queries'))
        # Affiliate summaries
        for aff in affiliates:
            self.stdout.write(self.style.HTTP_INFO(f"\n-- Affiliate summary: {aff}"))
            staff = CustomUser.objects.filter(
                Q(department__affiliate__name__iexact=aff) | Q(affiliate__name__iexact=aff),
                is_active=True
            ).exclude(role='admin').order_by('id')
            self.stdout.write(f"  active staff: {staff.count()}")
            # List a few names
            for usr in staff[:10]:
                self.stdout.write(f"   - {usr.id} {usr.get_full_name()} <{usr.email}> role={usr.role} dept={getattr(getattr(usr,'department',None),'name',None)}")
            # Pending requests
            pending = LeaveRequest.objects.filter(
                Q(employee__department__affiliate__name__iexact=aff) | Q(employee__affiliate__name__iexact=aff),
                status='pending'
            ).order_by('-created_at')
            self.stdout.write(f"  pending requests: {pending.count()}")
            for lr in pending[:10]:
                emp = lr.employee
                ceo = ApprovalRoutingService.get_ceo_for_employee(emp)
                self.stdout.write(
                    f"   - lr#{lr.id} by {emp.get_full_name()} <{emp.email}> can_ceo_approve={ApprovalWorkflowService.can_user_approve(lr, ceo) if ceo else False} ceo={getattr(ceo,'email',None)}"
                )
        self.stdout.write(self.style.MIGRATE_LABEL('\nDone.'))
