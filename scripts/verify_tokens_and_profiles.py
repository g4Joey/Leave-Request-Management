"""Bulk verification of JWT token issuance and profile data consistency.

Runs through the normalized user seed list, attempts login against the
token endpoint, fetches the profile, and validates expected role,
affiliate, and (where applicable) department values.

Exit codes:
 0 - all users verified
 1 - one or more token failures
 2 - one or more profile fetch failures
 3 - data mismatches (role/affiliate/department)
"""
import os
import sys
import requests
from dataclasses import dataclass
from typing import Optional, List

DEFAULT_BASE = "http://127.0.0.1:8000/api"

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
class UserExpectation:
    email: str
    password: str
    role_label: str
    affiliate: Optional[str] = None
    department: Optional[str] = None

    def internal_role(self) -> str:
        return ROLE_MAP.get(self.role_label.strip(), self.role_label.strip().lower())


ADMIN_PASS = os.environ.get("ADMIN_PASS") or os.environ.get("ADMIN_PASSWORD") or "AdminChangeMe123!"

EXPECTATIONS: List[UserExpectation] = [
    UserExpectation(email="admin@umbcapital.com", password=ADMIN_PASS, role_label="admin", affiliate=None),
    UserExpectation(email="ceo@umbcapital.com", password="MerbanCEO", role_label="MERBANCEO", affiliate="Merban Capital"),  # CEO no department
    UserExpectation(email="sdslceo@umbcapital.com", password="KofiAmeyaw", role_label="SDSLCEO", affiliate="SDSL"),
    UserExpectation(email="sblceo@umbcapital.com", password="WinslowSackey", role_label="SBLCEO", affiliate="SBL"),
    UserExpectation(email="hradmin@umbcapital.com", password="1HRADMIN", role_label="HR", affiliate="Merban Capital", department="HR & Admin"),
    UserExpectation(email="asanunu@umbcapital.com", password="ABsanunu", role_label="staff", affiliate="SDSL"),
    UserExpectation(email="enartey@umbcapital.com", password="EstherN", role_label="senior staff", affiliate="SBL"),
    UserExpectation(email="gsafo@umbcapital.com", password="Georgesafo", role_label="senior staff", affiliate="Merban Capital", department="IT"),
    UserExpectation(email="aakorfu@umbcapital.com", password="AustineAkorfu", role_label="junior staff", affiliate="Merban Capital", department="IT"),
    UserExpectation(email="jmankoe@umbcapital.com", password="Atokwamena", role_label="manager", affiliate="Merban Capital", department="IT"),
]


def obtain_token(base_url: str, email: str, password: str):
    url = f"{base_url}/auth/token/"
    resp = requests.post(url, json={"username": email, "password": password})
    return resp


def fetch_profile(base_url: str, token: str):
    url = f"{base_url}/users/me/"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    return resp


def main():
    base_url = os.environ.get("API_BASE", DEFAULT_BASE)
    print(f"[verify] Using base API: {base_url}")

    token_failures = []
    profile_failures = []
    mismatches = []

    for exp in EXPECTATIONS:
        print(f"[verify] Attempting login for {exp.email}")
        token_resp = obtain_token(base_url, exp.email, exp.password)
        if token_resp.status_code != 200:
            token_failures.append((exp.email, token_resp.status_code, token_resp.text))
            print(f"  TOKEN FAIL status={token_resp.status_code}")
            continue
        access = token_resp.json().get("access")
        if not access:
            token_failures.append((exp.email, token_resp.status_code, token_resp.text))
            print("  TOKEN MISSING access field")
            continue
        prof_resp = fetch_profile(base_url, access)
        if prof_resp.status_code != 200:
            profile_failures.append((exp.email, prof_resp.status_code, prof_resp.text))
            print(f"  PROFILE FAIL status={prof_resp.status_code}")
            continue
        data = prof_resp.json()
        actual_role = data.get("role") or data.get("role_display")
        # Normalize affiliate: may be a dict or a string
        raw_affiliate = data.get("affiliate") or data.get("affiliate_name")
        if isinstance(raw_affiliate, dict):
            actual_affiliate = raw_affiliate.get("name")
        else:
            actual_affiliate = raw_affiliate
        # Normalize department: may be None, dict, or string
        raw_department = data.get("department") or data.get("department_name")
        if isinstance(raw_department, dict):
            actual_department = raw_department.get("name")
        else:
            actual_department = raw_department
        expected_role = exp.internal_role()
        expected_aff = exp.affiliate
        expected_dept = exp.department
        role_ok = actual_role == expected_role
        aff_ok = actual_affiliate == expected_aff
        dept_ok = (expected_dept == actual_department) if expected_dept else (actual_department in (None, ""))
        if not (role_ok and aff_ok and dept_ok):
            mismatches.append({
                "email": exp.email,
                "expected": (expected_role, expected_aff, expected_dept),
                "actual": (actual_role, actual_affiliate, actual_department),
                "flags": {
                    "role_ok": role_ok,
                    "affiliate_ok": aff_ok,
                    "department_ok": dept_ok,
                },
            })
            print(f"  DATA MISMATCH role_ok={role_ok} aff_ok={aff_ok} dept_ok={dept_ok}")
        else:
            print("  OK")

    print(f"\n[verify] Summary: Token failures: {len(token_failures)} Profile failures: {len(profile_failures)} Mismatches: {len(mismatches)}")
    if token_failures:
        print("-- Token Failures --")
        for f in token_failures:
            print(f"  {f[0]} status={f[1]} body={f[2][:120]}")
    if profile_failures:
        print("-- Profile Failures --")
        for f in profile_failures:
            print(f"  {f[0]} status={f[1]} body={f[2][:120]}")
    if mismatches:
        print("-- Data Mismatches --")
        for m in mismatches:
            print(f"  {m['email']} expected={m['expected']} actual={m['actual']} flags={m['flags']}")

    if token_failures:
        sys.exit(1)
    if profile_failures:
        sys.exit(2)
    if mismatches:
        sys.exit(3)
    print("[verify] All users verified successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()
