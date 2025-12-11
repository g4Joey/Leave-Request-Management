"""Simple local login verification script.

Usage (after installing requirements and having server running on :8000):
  python quick_login_check.py --email admin@umbcapital.com --password AdminChangeMe123!

Exits with non-zero status if login fails.
"""

import argparse
import sys
import requests

DEFAULT_BASE = "http://127.0.0.1:8000/api"

def obtain_token(base_url: str, email: str, password: str):
    url = f"{base_url}/auth/token/"
    resp = requests.post(url, json={"username": email, "password": password})
    if resp.status_code != 200:
        return None, resp
    data = resp.json()
    return data.get("access"), resp

def fetch_profile(base_url: str, token: str):
    url = f"{base_url}/users/me/"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    return resp

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="Login email/username")
    parser.add_argument("--password", required=True, help="Login password")
    parser.add_argument("--base", default=DEFAULT_BASE, help="Base API URL (default http://127.0.0.1:8000/api)")
    args = parser.parse_args()

    print(f"[login-check] Attempting token at {args.base} for {args.email}")
    token, token_resp = obtain_token(args.base, args.email, args.password)
    if not token:
        print(f"FAILED: Token request status={token_resp.status_code} body={token_resp.text}")
        sys.exit(1)

    print("[login-check] Token acquired.")
    profile_resp = fetch_profile(args.base, token)
    if profile_resp.status_code != 200:
        print(f"PROFILE FETCH FAILED status={profile_resp.status_code} body={profile_resp.text}")
        sys.exit(2)

    profile = profile_resp.json()
    role = profile.get("role") or profile.get("role_display")
    print("[login-check] SUCCESS")
    print(f"User role: {role}")
    print(f"User affiliate: {profile.get('affiliate')}")
    print(f"Name: {profile.get('first_name')} {profile.get('last_name')}")

if __name__ == "__main__":
    main()
