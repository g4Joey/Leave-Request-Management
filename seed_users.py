import os
import django

# --- Setup Django Environment ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import Affiliate, Department
from leaves.models import LeaveType

# --- User Data ---
# A list of dictionaries, each representing a user to be created.
USER_DATA = [
    {
        "username": "ceo@umbcapital.com",
        "first_name": "Benjamin",
        "last_name": "Ackah",
        "email": "ceo@umbcapital.com",
        "password": "MerbanCEO",
        "role": "ceo",
        "affiliate": "Merban Capital",
        "department": None,
    },
    {
        "username": "sdslceo@umbcapital.com",
        "first_name": "Kofi",
        "last_name": "Ameyaw",
        "email": "sdslceo@umbcapital.com",
        "password": "KofiAmeyaw",
        "role": "ceo",
        "affiliate": "SDSL",
        "department": None,
    },
    {
        "username": "sblceo@umbcapital.com",
        "first_name": "Winslow",
        "last_name": "Sackey",
        "email": "sblceo@umbcapital.com",
        "password": "WinslowSackey",
        "role": "ceo",
        "affiliate": "SBL",
        "department": None,
    },
    {
        "username": "hradmin@umbcapital.com",
        "first_name": "Nana Ama",
        "last_name": "Daatano",
        "email": "hradmin@umbcapital.com",
        "password": "1HRADMIN",
        "role": "hr",
        "affiliate": "Merban Capital",
        "department": "HR & Admin",
    },
    {
        "username": "asanunu",
        "first_name": "Abdul",
        "last_name": "Sanunu",
        "email": "asanunu@umbcapital.com",
        "password": "ABsanunu",
        "role": "junior_staff",
        "affiliate": "SDSL",
        "department": None,
    },
    {
        "username": "enartey",
        "first_name": "Esther",
        "last_name": "Nartey",
        "email": "enartey@umbcapital.com",
        "password": "EstherN",
        "role": "junior_staff",
        "affiliate": "SBL",
        "department": None,
    },
    {
        "username": "gsafo",
        "first_name": "George",
        "last_name": "Safo",
        "email": "gsafo@umbcapital.com",
        "password": "Georgesafo",
        "role": "senior_staff",
        "affiliate": "Merban Capital",
        "department": "IT",
    },
    {
        "username": "aakorfu",
        "first_name": "Augustine",
        "last_name": "Akorfu",
        "email": "aakorfu@umbcapital.com",
        "password": "AustineAkorfu",
        "role": "junior_staff",
        "affiliate": "Merban Capital",
        "department": "IT",
    },
    {
        "username": "jmankoe",
        "first_name": "Joseph",
        "last_name": "Mankoe",
        "email": "jmankoe@umbcapital.com",
        "password": "Atokwamena",
        "role": "manager",
        "affiliate": "Merban Capital",
        "department": "IT",
    },
]

def seed_database():
    """
    Populates the database with affiliates, departments, users, and a default leave type.
    """
    CustomUser = get_user_model()
    print("--- Starting Database Seeding ---")

    # --- Ensure baseline Leave Types ---
    for lt_name in ["Annual Leave", "Casual Leave"]:
        lt, created = LeaveType.objects.get_or_create(
            name=lt_name,
            defaults={'is_active': True}
        )
        if created:
            print(f"Created Leave Type: {lt_name}")

    for user_data in USER_DATA:
        # --- Get or Create Affiliate ---
        affiliate_name = user_data.get("affiliate")
        affiliate = None
        if affiliate_name:
            affiliate, created = Affiliate.objects.get_or_create(name=affiliate_name)
            if created:
                print(f"Created Affiliate: {affiliate.name}")

        # --- Get or Create Department ---
        department_name = user_data.get("department")
        department = None
        if department_name:
            department, created = Department.objects.get_or_create(
                name=department_name,
                defaults={'affiliate': affiliate}
            )
            if created:
                print(f"Created Department: {department.name}")

        # --- Create User ---
        username = user_data["username"]
        if not CustomUser.objects.filter(username=username).exists():
            print(f"Creating user: {username}...")
            user = CustomUser.objects.create_user(
                username=username,
                email=user_data["email"],
                password=user_data["password"],
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
            )
            
            # --- Assign Role, Affiliate, Department, and Employee ID ---
            user.role = user_data["role"]
            user.affiliate = affiliate
            user.department = department
            user.employee_id = username  # Use username as employee_id
            user.save()
            
            print(f"  - User '{user.username}' created successfully.")
        else:
            print(f"User '{username}' already exists. Skipping.")

    print("\n--- Database Seeding Complete ---")

if __name__ == "__main__":
    seed_database()
