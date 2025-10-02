from django.db import transaction
from .models import LeaveType, LeaveBalance
from users.models import EmploymentGrade, CustomUser


def apply_grade_entitlements(grade: EmploymentGrade, year=None):
    """Propagate grade entitlements to users' LeaveBalance.

    Args:
        grade: EmploymentGrade whose entitlements we apply.
        year: Optional year; defaults to current year of LeaveBalance logic.
    """
    from django.utils import timezone
    if year is None:
        year = timezone.now().year

    ent_map = {ge.leave_type_id: ge.entitled_days for ge in grade.entitlements.select_related('leave_type')}
    if not ent_map:
        return 0

    users = CustomUser.objects.filter(grade=grade, is_active=True)
    count = 0
    with transaction.atomic():
        for user in users:
            for lt_id, entitled in ent_map.items():
                lb, _ = LeaveBalance.objects.get_or_create(
                    user=user, leave_type_id=lt_id, year=year,
                    defaults={'entitled_days': entitled}
                )
                if lb.entitled_days != entitled:
                    lb.entitled_days = entitled
                    lb.save(update_fields=['entitled_days'])
                    count += 1
    return count
