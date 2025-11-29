"""Normalize user records for local development.

- Ensures username == email for all users.
- Assigns provided first_name, last_name, role (mapped to internal choices), affiliate, department.
- Sets passwords (hashed) from provided cleartext for dev only.
- Creates affiliates / departments if missing.

SECURITY: Plain text passwords are ONLY used here for initial local dev seeding. In production, NEVER commit real secrets.
"""
import os, sys
from dataclasses import dataclass
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "leave_management.settings")
import django  # noqa: E402

django.setup()

from users.models import CustomUser, Affiliate, Department  # noqa: E402
from django.db import transaction  # noqa: E402

# Mapping external role labels to internal system role choices
ROLE_MAP = {
    "MERBANCEO": "ceo",
    "SDSLCEO": "ceo",
    "SBLCEO": "ceo",
    "senior staff": "senior_staff",
    "junior staff": "junior_staff",
    "staff": "junior_staff",
    "HR": "hr",
    "manager": "manager",
    "admin": "admin",
}

@dataclass
class UserSeed:
    email: str
    first_name: str
    last_name: str
    role_label: str  # external label; will be mapped
    affiliate: str
    department: Optional[str] = None
    password: str = "ChangeMeLocal123!"

    def internal_role(self) -> str:
        return ROLE_MAP.get(self.role_label.strip(), self.role_label.strip().lower())

# Provided seeds (ceos, hr, staff, merban staff & manager)
SEEDS = [
    UserSeed(email="ceo@umbcapital.com", first_name="Benjamin", last_name="Ackah", role_label="MERBANCEO", affiliate="Merban Capital", password="MerbanCEO"),
    UserSeed(email="sdslceo@umbcapital.com", first_name="Kofi", last_name="Ameyaw", role_label="SDSLCEO", affiliate="SDSL", password="KofiAmeyaw"),
    UserSeed(email="sblceo@umbcapital.com", first_name="Winslow", last_name="Sackey", role_label="SBLCEO", affiliate="SBL", password="WinslowSackey"),
    UserSeed(email="hradmin@umbcapital.com", first_name="Nana Ama", last_name="Daatano", role_label="HR", affiliate="Merban Capital", password="1HRADMIN", department="HR & Admin"),
    UserSeed(email="asanunu@umbcapital.com", first_name="Abdul", last_name="Sanunu", role_label="staff", affiliate="SDSL", password="ABsanunu"),
    UserSeed(email="enartey@umbcapital.com", first_name="Esther", last_name="Nartey", role_label="senior staff", affiliate="SBL", password="EstherN"),
    UserSeed(email="gsafo@umbcapital.com", first_name="George", last_name="Safo", role_label="senior staff", affiliate="Merban Capital", department="IT", password="Georgesafo"),
    UserSeed(email="aakorfu@umbcapital.com", first_name="Augustine", last_name="Akorfu", role_label="junior staff", affiliate="Merban Capital", department="IT", password="AustineAkorfu"),
    UserSeed(email="jmankoe@umbcapital.com", first_name="Joseph", last_name="Mankoe", role_label="manager", affiliate="Merban Capital", department="IT", password="Atokwamena"),
]

# Affiliate names and Merban departments specified
MERBAN_DEPARTMENTS = ["HR & Admin", "IT"]

@transaction.atomic
def normalize():
    # Ensure Affiliates exist
    affiliates_cache = {}
    for aff_name in sorted({s.affiliate for s in SEEDS}):
        aff, _ = Affiliate.objects.get_or_create(name=aff_name)
        affiliates_cache[aff_name] = aff

    # Ensure Merban departments exist (only for Merban Capital affiliate)
    merban_aff = affiliates_cache.get("Merban Capital")
    dept_cache = {}
    if merban_aff:
        for d in MERBAN_DEPARTMENTS:
            dept, _ = Department.objects.get_or_create(name=d, affiliate=merban_aff)
            dept_cache[d] = dept

    # Process each seed
    updated = []
    created = []
    for seed in SEEDS:
        role_internal = seed.internal_role()
        aff = affiliates_cache[seed.affiliate]
        dept = None
        if seed.department:
            if seed.affiliate == "Merban Capital":
                dept = dept_cache.get(seed.department)
                if not dept:
                    raise ValueError(f"Department '{seed.department}' not provisioned for Merban Capital")
            else:
                # Non-Merban department provided -> disallow per requirements
                raise ValueError(f"Department '{seed.department}' provided for non-Merban affiliate '{seed.affiliate}'")
        user_qs = CustomUser.objects.filter(email__iexact=seed.email)
        if user_qs.exists():
            user = user_qs.first()
            # Update fields
            user.username = seed.email  # username == email
            user.first_name = seed.first_name
            user.last_name = seed.last_name
            user.role = role_internal
            user.affiliate = aff
            # Department requirements: Merban users must have department if in list; CEOs may intentionally lack
            if dept:
                user.department = dept
            elif seed.affiliate == "Merban Capital" and role_internal != "ceo":
                # Enforce department presence for non-CEO Merban users
                raise ValueError(f"Missing department for Merban user {seed.email}")
            user.set_password(seed.password)
            user.save()
            updated.append(seed.email)
        else:
            # employee_id must be unique; derive simple placeholder if absent
            employee_id = f"EMP{CustomUser.objects.count()+1:04d}"
            user = CustomUser(
                email=seed.email,
                username=seed.email,
                first_name=seed.first_name,
                last_name=seed.last_name,
                role=role_internal,
                affiliate=aff,
                employee_id=employee_id,
            )
            if dept:
                user.department = dept
            elif seed.affiliate == "Merban Capital" and role_internal != "ceo":
                raise ValueError(f"Missing department for new Merban user {seed.email}")
            user.set_password(seed.password)
            user.save()
            created.append(seed.email)

    # Ensure every Merban Capital non-CEO has a department
    merban_users_without_dept = CustomUser.objects.filter(affiliate=merban_aff, department__isnull=True).exclude(role="ceo")
    if merban_users_without_dept.exists():
        raise ValueError(f"Found Merban Capital users without department: {[u.email for u in merban_users_without_dept]}")

    # Set Merban IT HOD and manager relationships so manager approvals route correctly
    try:
      it_dept = Department.objects.get(name__iexact="IT", affiliate=merban_aff)
      # HOD is the Merban manager user (jmankoe); fall back by role & affiliate
      hod_user = (
          CustomUser.objects.filter(username__iexact="jmankoe").first()
          or CustomUser.objects.filter(role='manager', affiliate=merban_aff).first()
      )
      if hod_user and it_dept.hod_id != hod_user.id:
          it_dept.hod = hod_user
          it_dept.save(update_fields=['hod'])
      # Assign manager for staff in this department where missing and not the HOD
      staff_qs = CustomUser.objects.filter(affiliate=merban_aff, department=it_dept).exclude(id=getattr(hod_user,'id',None))
      for emp in staff_qs:
          if emp.role in ['junior_staff', 'senior_staff'] and (emp.manager_id != getattr(hod_user,'id',None)):
              emp.manager = hod_user
              emp.save(update_fields=['manager'])

      # Ensure HR & Admin department HOD is the HR user
      hr_admin_dept = Department.objects.filter(name__iexact="HR & Admin", affiliate=merban_aff).first()
      hr_user = CustomUser.objects.filter(email__iexact="hradmin@umbcapital.com").first() or CustomUser.objects.filter(role='hr', affiliate=merban_aff).first()
      if hr_admin_dept and hr_user and hr_admin_dept.hod_id != hr_user.id:
          hr_admin_dept.hod = hr_user
          hr_admin_dept.save(update_fields=['hod'])
    except Exception as e:
      # Non-fatal; print for visibility in local runs
      print("[normalize] Skipped HOD/manager assignment:", e)

    print("Users created:", created)
    print("Users updated:", updated)
    print("Total users:", CustomUser.objects.count())
    print("Summary (email, role, affiliate, department):")
    for u in CustomUser.objects.all().order_by("email"):
        print(f"  {u.email} | {u.role} | {u.affiliate and u.affiliate.name} | {u.department and u.department.name}")
    print("NOTE: Passwords have been hashed. Use the provided plaintext values for local login only.")

if __name__ == "__main__":
    normalize()
