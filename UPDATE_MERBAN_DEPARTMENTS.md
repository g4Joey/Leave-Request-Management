# Update Merban Capital Departments - Digital Ocean Deployment

## Quick Deploy Steps

### Option 1: SSH into Digital Ocean Droplet (Recommended)

1. **SSH into your droplet:**
   ```bash
   ssh root@your-droplet-ip
   ```

2. **Navigate to your project directory:**
   ```bash
   cd /path/to/Leave-Request-Management
   ```

3. **Pull the latest changes:**
   ```bash
   git pull origin main
   ```

4. **Run the management command:**
   ```bash
   python manage.py update_merban_departments
   ```

5. **Restart your application:**
   ```bash
   # If using systemd
   sudo systemctl restart gunicorn
   
   # If using Docker
   docker-compose restart web
   
   # If using pm2
   pm2 restart all
   ```

---

### Option 2: Using Django Shell Remotely

If you can't pull changes, SSH in and run directly in Django shell:

```bash
ssh root@your-droplet-ip
cd /path/to/Leave-Request-Management
python manage.py shell
```

Then paste this script:

```python
from django.db import transaction
from users.models import Department, Affiliate

with transaction.atomic():
    merban = Affiliate.objects.get(name='Merban Capital')
    
    # 1. Accounts & Compliance → Finance & Accounts
    Department.objects.filter(name__iexact='Accounts & Compliance', affiliate=merban).update(name='Finance & Accounts (Merban Capital)')
    
    # 2. Government Securities → Government Securities (Merban Capital)
    Department.objects.filter(name__iexact='Government Securities', affiliate=merban).update(name='Government Securities (Merban Capital)')
    
    # 3. PENSIONS → Pensions & Provident Funds
    Department.objects.filter(name__iexact='PENSIONS', affiliate=merban).update(name='Pensions & Provident Funds (Merban Capital)')
    
    # 4. IT → IT (Merban Capital)
    Department.objects.filter(name__iexact='IT', affiliate=merban).update(name='IT (Merban Capital)')
    
    # 5. IHL → Client Service/Marketing
    Department.objects.filter(name__iexact='IHL', affiliate=merban).update(name='Client Service/Marketing (Merban Capital)')
    
    # 6. Client Service → HR & Admin
    Department.objects.filter(name__iexact='Client Service', affiliate=merban).update(name='HR & Admin (Merban Capital)')
    
    # 7. STOCKBROKERS → Private Wealth & Mutual Fund
    Department.objects.filter(name__iexact='STOCKBROKERS', affiliate=merban).update(name='Private Wealth & Mutual Fund (Merban Capital)')
    
    # 8. SDSL department → Corporate Finance
    Department.objects.filter(name__iexact='SDSL', affiliate=merban).update(name='Corporate Finance (Merban Capital)')
    
    # 9. Create Audit
    Department.objects.get_or_create(name='Audit (Merban Capital)', affiliate=merban)
    
    # 10. Create Compliance
    Department.objects.get_or_create(name='Compliance (Merban Capital)', affiliate=merban)
    
    print("✓ All departments updated successfully!")
    
    # Verify
    print("\nAll Merban Capital Departments:")
    for dept in Department.objects.filter(affiliate=merban).order_by('name'):
        print(f"  • {dept.name} ({dept.customuser_set.count()} staff)")
```

---

### Option 3: Deploy via Git Push (If using automated deployment)

1. **Commit the management command:**
   ```bash
   git add users/management/commands/update_merban_departments.py
   git commit -m "feat: add management command to update Merban Capital departments"
   git push origin main
   ```

2. **Wait for auto-deployment or trigger manually**

3. **SSH in and run the command:**
   ```bash
   ssh root@your-droplet-ip
   cd /path/to/Leave-Request-Management
   python manage.py update_merban_departments
   sudo systemctl restart gunicorn  # or your app server
   ```

---

## Changes Being Made

### Department Renames:
1. ✅ Accounts & Compliance → **Finance & Accounts (Merban Capital)**
2. ✅ Government Securities → **Government Securities (Merban Capital)**
3. ✅ PENSIONS → **Pensions & Provident Funds (Merban Capital)**
4. ✅ IT → **IT (Merban Capital)** *(currently has 3 staff)*
5. ✅ IHL → **Client Service/Marketing (Merban Capital)**
6. ✅ Client Service → **HR & Admin (Merban Capital)** *(has HR user)*
7. ✅ Executive → **Keep as is** *(has Benjamin Ackah)*
8. ✅ STOCKBROKERS → **Private Wealth & Mutual Fund (Merban Capital)**
9. ✅ SDSL department → **Corporate Finance (Merban Capital)** *(NOT the affiliate)*

### New Departments:
10. ✅ **Audit (Merban Capital)**
11. ✅ **Compliance (Merban Capital)**

---

## Verification After Running

Check that departments appear correctly:

```bash
python manage.py shell
```

```python
from users.models import Department, Affiliate

merban = Affiliate.objects.get(name='Merban Capital')
depts = Department.objects.filter(affiliate=merban).order_by('name')

print(f"\nTotal Merban Departments: {depts.count()}\n")
for dept in depts:
    staff_count = dept.customuser_set.count()
    manager = dept.manager or "No manager"
    print(f"• {dept.name}")
    print(f"  Staff: {staff_count}, Manager: {manager}\n")
```

---

## Troubleshooting

### If departments don't show on frontend:

1. **Clear browser cache** (Ctrl + Shift + R)

2. **Check frontend is calling correct API:**
   - Open browser DevTools → Network tab
   - Look for `/api/affiliates/{id}/departments/` call
   - Verify it returns the updated department names

3. **Restart frontend dev server** (if applicable):
   ```bash
   cd frontend
   npm run dev
   ```

4. **Check if frontend build needs update:**
   ```bash
   cd frontend
   npm run build
   ```

---

## Database Connection Info

Since you're using Digital Ocean Managed Database:
- The command uses Django's existing database settings
- Connection is configured in `settings.py` or `settings_production.py`
- No need to modify database credentials

**Note:** Make sure your `DATABASES` setting in production points to your Digital Ocean managed database.

---

## Support Commands

**List all affiliates:**
```bash
python manage.py shell -c "from users.models import Affiliate; [print(f'{a.id}: {a.name}') for a in Affiliate.objects.all()]"
```

**Count departments per affiliate:**
```bash
python manage.py shell -c "from users.models import Department; from django.db.models import Count; [print(f'{a[\"affiliate__name\"]}: {a[\"total\"]} depts') for a in Department.objects.values('affiliate__name').annotate(total=Count('id'))]"
```

---

## Next Steps After Running

1. ✅ Verify departments appear in Merban Capital affiliate page
2. ✅ Assign managers to new departments (Audit & Compliance)
3. ✅ Move staff to appropriate departments if needed
4. ✅ Test leave request workflow with new structure
