"""One-time username normalization.

Sets every user's `username` field to exactly match their `email` if
they differ (case-insensitive comparison). Prints a summary of changes.

Usage:
  python scripts/sync_usernames_to_emails.py

Safe to re-run; only updates mismatches.
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "leave_management.settings")
import django  # noqa: E402

django.setup()

from users.models import CustomUser  # noqa: E402
from django.db import transaction  # noqa: E402


def normalize_usernames():
    changed = []
    unchanged = 0
    with transaction.atomic():
        for user in CustomUser.objects.all():
            email = (user.email or '').strip()
            username = (user.username or '').strip()
            if not email:
                continue  # skip users without email
            if username.lower() != email.lower():
                user.username = email
                user.save(update_fields=["username"])
                changed.append((email, username, user.username))
            else:
                unchanged += 1
    print(f"Total users processed: {unchanged + len(changed)}")
    print(f"Changed usernames: {len(changed)}")
    for old in changed:
        print(f"  {old[0]}: {old[1]} -> {old[2]}")
    print(f"Unchanged usernames: {unchanged}")


if __name__ == "__main__":
    normalize_usernames()
