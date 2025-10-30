from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import CustomUser, Department, Affiliate


class Command(BaseCommand):
    help = "Assign HODs based on rules: HR & Admin -> HR user; IT -> 'jmankoe'; ensure 'jmankoe' not HOD elsewhere."

    def add_arguments(self, parser):
        parser.add_argument(
            "--affiliate",
            dest="affiliate_name",
            default="MERBAN CAPITAL",
            help="Affiliate name to scope departments (default: 'MERBAN CAPITAL')",
        )
        parser.add_argument(
            "--it-manager",
            dest="it_manager_username",
            default="jmankoe",
            help="Username to assign as IT HOD (default: 'jmankoe')",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        affiliate_name = options["affiliate_name"]
        it_manager_username = options["it_manager_username"]

        self.stdout.write(f"[assign_hods] Start for affiliate: {affiliate_name}")

        try:
            affiliate = Affiliate.objects.get(name__iexact=affiliate_name)
        except Affiliate.DoesNotExist:
            self.stderr.write(f"Affiliate '{affiliate_name}' not found")
            return

        # 1) HR & Admin -> assign HOD to any active HR user (prefer same affiliate)
        hr_user = (
            CustomUser.objects.filter(role="hr", is_active=True, affiliate=affiliate).first()
            or CustomUser.objects.filter(role="hr", is_active=True).first()
        )
        hr_admin_dept = Department.objects.filter(affiliate=affiliate, name__iexact="HR & Admin").first()
        if hr_admin_dept and hr_user:
            if hr_admin_dept.hod_id != hr_user.id:
                hr_admin_dept.hod = hr_user
                hr_admin_dept.save(update_fields=["hod"])
                self.stdout.write(
                    f"[assign_hods] Set HOD for 'HR & Admin' to {hr_user.get_full_name()} ({hr_user.username})"
                )
            else:
                self.stdout.write("[assign_hods] HOD for 'HR & Admin' already correct")
        else:
            self.stderr.write("[assign_hods] Could not set HOD for 'HR & Admin' (missing dept or HR user)")

        # 2) IT -> assign HOD to jmankoe
        it_dept = Department.objects.filter(affiliate=affiliate, name__iexact="IT").first()
        it_manager = CustomUser.objects.filter(username__iexact=it_manager_username, is_active=True).first()
        if it_dept and it_manager:
            if it_dept.hod_id != it_manager.id:
                it_dept.hod = it_manager
                it_dept.save(update_fields=["hod"])
                self.stdout.write(
                    f"[assign_hods] Set HOD for 'IT' to {it_manager.get_full_name()} ({it_manager.username})"
                )
            else:
                self.stdout.write("[assign_hods] HOD for 'IT' already correct")

            # Ensure jmankoe is not HOD for any other department
            other_hod_depts = Department.objects.filter(hod=it_manager).exclude(pk=it_dept.pk)
            cleared = 0
            for dept in other_hod_depts:
                dept.hod = None
                dept.save(update_fields=["hod"])
                cleared += 1
                self.stdout.write(
                    f"[assign_hods] Cleared HOD '{it_manager.username}' from department '{dept.name}'"
                )
            if cleared == 0:
                self.stdout.write("[assign_hods] No other departments had 'jmankoe' as HOD")
        else:
            self.stderr.write(
                "[assign_hods] Could not set HOD for 'IT' (missing IT department or user 'jmankoe')"
            )

        self.stdout.write("[assign_hods] Completed")
