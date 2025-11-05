import os
import sys
from pathlib import Path
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import django
django.setup()

from django.contrib.auth import get_user_model
from users.models import Affiliate, CustomUser


def main():
    User = get_user_model()
    merban = Affiliate.objects.filter(name__iexact='MERBAN CAPITAL').first()
    if not merban:
        print('Affiliate MERBAN CAPITAL not found.'); return

    # Gather CEO candidates
    ceos = list(User.objects.filter(role='ceo', is_active=True))
    print(f"Active CEOs found: {len(ceos)}")
    for c in ceos:
        dep_aff = getattr(getattr(c, 'department', None), 'affiliate', None)
        print(f" - id={c.id} email={c.email} affiliate={getattr(getattr(c,'affiliate',None),'name',None)} dept_aff={getattr(dep_aff,'name',None)}")

    # Prefer CEOs already linked to Merban via affiliate or department
    ceos_merban_aff = [c for c in ceos if getattr(getattr(c,'affiliate',None),'id',None) == merban.id]
    ceos_merban_dept = [c for c in ceos if getattr(getattr(getattr(c,'department',None),'affiliate',None),'id',None) == merban.id]

    target = None
    if ceos_merban_aff:
        target = ceos_merban_aff[0]
        print(f"CEO already linked to Merban via affiliate: id={target.id} {target.email}")
    elif ceos_merban_dept:
        target = ceos_merban_dept[0]
        print(f"CEO linked to Merban via department: id={target.id} {target.email}")
    else:
        # Fallback heuristic: pick first CEO with no affiliate (likely misconfigured) if only one
        ceos_no_aff = [c for c in ceos if getattr(c,'affiliate',None) is None]
        if len(ceos_no_aff) == 1:
            target = ceos_no_aff[0]
            print(f"Single CEO without affiliate found, selecting: id={target.id} {target.email}")

    if not target:
        print("No unambiguous Merban CEO identified. Please review the above list and set manually if needed.")
        return

    # Assign affiliate explicitly
    if getattr(getattr(target,'affiliate',None),'id',None) != merban.id:
        target.affiliate = merban
        target.save(update_fields=['affiliate'])
        print(f"Updated CEO {target.id} -> affiliate={merban.name}")
    else:
        print(f"CEO {target.id} already has affiliate {merban.name}")

if __name__ == '__main__':
    main()
