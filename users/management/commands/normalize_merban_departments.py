from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import Department, Affiliate, CustomUser


CANONICAL_NAMES = [
    'Finance & Accounts',
    'Government Securities',
    'Pensions & Provident Fund',
    'Private Wealth & Mutual Fund',
    'HR & Admin',
    'Client Service/Marketing',
    'Corporate Finance',
    'IT',
    'Compliance',
    'Audit',
]

ALIASES = {
    'pensions & provident funds': 'Pensions & Provident Fund',
}


def base_name(name: str) -> str:
    if not name:
        return ''
    n = name.strip()
    # Strip any parenthetical affiliate suffix e.g., " (Merban Capital)"
    lower = n.lower()
    suffix = ' (merban capital)'
    if lower.endswith(suffix):
        n = n[: -len(suffix)]
    return n.strip()


def match_canonical(n: str) -> str:
    b = base_name(n)
    # First apply alias mapping if present
    if b.lower() in ALIASES:
        return ALIASES[b.lower()]
    for canon in CANONICAL_NAMES:
        if b.lower() == canon.lower():
            return canon
    return b or n


class Command(BaseCommand):
    help = 'Normalize Merban Capital departments: strip suffix, merge duplicates, set affiliate, and create missing.'

    def handle(self, *args, **options):
        self.stdout.write('Normalizing Merban Capital departments...')
        merban = Affiliate.objects.filter(name__iexact='MERBAN CAPITAL').first()
        if not merban:
            self.stdout.write(self.style.ERROR('Affiliate "MERBAN CAPITAL" not found.'))
            return

        with transaction.atomic():
            # Group departments by canonical base name
            groups = {}
            for dept in Department.objects.all().select_related('affiliate'):
                canon = match_canonical(dept.name)
                groups.setdefault(canon.lower(), []).append(dept)

            # Ensure each canonical Merban department has exactly one Department row
            for canon in CANONICAL_NAMES:
                items = groups.get(canon.lower(), [])
                if not items:
                    # Create if missing
                    d = Department.objects.create(name=canon, description='', affiliate=merban)
                    self.stdout.write(self.style.SUCCESS(f'✓ Created missing department: {canon} (id={d.pk})'))
                    groups.setdefault(canon.lower(), []).append(d)
                    items = groups[canon.lower()]

                # Choose primary robustly to avoid unique collisions when saving:
                # 1) exact canonical name + merban affiliate
                exact_merban = [d for d in items if d.name == canon and d.affiliate_id == merban.id]
                # 2) exact canonical name (any affiliate)
                exact_any = [d for d in items if d.name == canon]
                # 3) any merban-linked dept
                merban_candidates = [d for d in items if d.affiliate_id == merban.id]
                # 4) fallback: oldest
                if exact_merban:
                    primary = sorted(exact_merban, key=lambda x: x.pk)[0]
                elif exact_any:
                    primary = sorted(exact_any, key=lambda x: x.pk)[0]
                elif merban_candidates:
                    primary = sorted(merban_candidates, key=lambda x: x.pk)[0]
                else:
                    primary = sorted(items, key=lambda x: x.pk)[0]

                # Normalize primary: set name and affiliate
                updates = {}
                # Only set name if not already canonical
                if primary.name != canon:
                    primary.name = canon
                    updates['name'] = True
                # Only set affiliate if not already merban
                if primary.affiliate_id != merban.id:
                    primary.affiliate = merban
                    updates['affiliate'] = True
                if updates:
                    try:
                        primary.save()
                        self.stdout.write(f'✓ Normalized primary: {canon} (id={primary.pk})')
                    except Exception as e:
                        # If a unique constraint occurs, try switching primary to an existing exact record
                        conflict = Department.objects.filter(name=canon, affiliate=merban).exclude(pk=primary.pk).first()
                        if conflict:
                            # Swap: move users from would-be-primary into conflict (now primary), delete it, and set primary to conflict
                            moved = CustomUser.objects.filter(department=primary).update(department=conflict)
                            try:
                                old_pk = primary.pk
                                primary.delete()
                                primary = conflict
                                self.stdout.write(f'! Switched primary due to conflict; moved {moved} users from id={old_pk} to id={primary.pk}')
                            except Exception as de:
                                self.stdout.write(self.style.WARNING(f'! Could not delete conflicting dept id={old_pk}: {de}'))
                        else:
                            raise

                # Merge duplicates into primary
                for d in items:
                    if d.pk == primary.pk:
                        continue
                    moved = CustomUser.objects.filter(department=d).update(department=primary)
                    try:
                        d.delete()
                        self.stdout.write(f'- Merged duplicate dept id={d.pk} into {canon}; moved {moved} users.')
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'! Could not delete duplicate id={d.pk}: {e}'))

            # Also clean up any leftover departments that had the suffix but are not in canonical list
            for dept in Department.objects.all():
                bn = base_name(dept.name)
                if dept.name != bn:
                    dept.name = bn
                    dept.save(update_fields=['name'])
                    self.stdout.write(f'• Stripped suffix from non-canonical dept: {bn} (id={dept.pk})')

        # Summary
        self.stdout.write('\nSummary (Merban Capital):')
        for d in Department.objects.filter(affiliate=merban).order_by('name'):
            count = CustomUser.objects.filter(department=d, is_active=True).count()
            self.stdout.write(f'  - {d.name} (id={d.pk}, staff={count})')
        self.stdout.write(self.style.SUCCESS('Normalization complete.'))
