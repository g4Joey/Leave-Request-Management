# 🎯 MERBAN CAPITAL DEPARTMENT UPDATES - READY TO DEPLOY

**Date:** October 24, 2025  
**Status:** ✅ Ready for Digital Ocean Deployment  
**Branch:** main (4 commits ahead of origin)

---

## 📦 What's Been Prepared

### 1. **Backend Management Command**
**File:** `users/management/commands/update_merban_departments.py`

This Django management command will:
- ✅ Rename 8 existing departments with proper "(Merban Capital)" suffix
- ✅ Create 2 new departments (Audit & Compliance)
- ✅ Preserve staff assignments and department relationships
- ✅ Run in a database transaction (safe rollback on errors)
- ✅ Provide detailed output of all changes

### 2. **Frontend Display Order Updated**
**File:** `frontend/src/components/AffiliatePage.js`

The department display order has been updated to match new names:
```javascript
const desiredOrder = [
  'Finance & Accounts',
  'Government Securities',
  'Pensions & Provident Funds',
  'Private Wealth & Mutual Fund',
  'HR & Admin',
  'Client Service/Marketing',
  'Corporate Finance',
  'IT',
  'Compliance',
  'Audit',
  'Executive'
];
```

### 3. **Deployment Documentation**
- ✅ `UPDATE_MERBAN_DEPARTMENTS.md` - Detailed deployment guide
- ✅ `DEPLOY_CHECKLIST.md` - Quick deployment checklist
- ✅ `check_merban_departments.py` - Verification script

---

## 🔄 Changes to Be Applied

### Department Renames (8 departments)

| Current Name | New Name |
|--------------|----------|
| Accounts & Compliance | **Finance & Accounts (Merban Capital)** |
| Government Securities | **Government Securities (Merban Capital)** |
| PENSIONS | **Pensions & Provident Funds (Merban Capital)** |
| IT | **IT (Merban Capital)** |
| IHL | **Client Service/Marketing (Merban Capital)** |
| Client Service | **HR & Admin (Merban Capital)** *(has HR user)* |
| STOCKBROKERS | **Private Wealth & Mutual Fund (Merban Capital)** |
| SDSL | **Corporate Finance (Merban Capital)** |

### New Departments (2 new)

9. **Audit (Merban Capital)** - NEW
10. **Compliance (Merban Capital)** - NEW

### Unchanged (1 department)

- **Executive** - Kept as is (has Benjamin Ackah)

---

## 🚀 DEPLOYMENT STEPS

### Step 1: Push Changes to GitHub
```bash
git push origin main
```

### Step 2: SSH into Your Digital Ocean Droplet
```bash
ssh root@YOUR_DROPLET_IP
# Or use the Digital Ocean console in your browser
```

### Step 3: Pull Latest Code
```bash
cd /path/to/Leave-Request-Management
git pull origin main
```

### Step 4: Run the Management Command
```bash
python manage.py update_merban_departments
```

Expected output:
```
Starting department updates for Merban Capital...
Found Merban Capital affiliate (ID: X)
✓ Renamed: Accounts & Compliance → Finance & Accounts (Merban Capital)
✓ Renamed: Government Securities → Government Securities (Merban Capital)
...
✓ Created: Audit (Merban Capital)
✓ Created: Compliance (Merban Capital)
✓ All changes committed successfully!
```

### Step 5: Restart Your Application
```bash
# If using systemd with gunicorn:
sudo systemctl restart gunicorn

# If using Docker:
docker-compose restart web

# If using pm2:
pm2 restart all
```

### Step 6: Rebuild Frontend (if needed)
```bash
cd frontend
npm run build
```

---

## ✅ Verification Steps

### 1. Via Django Shell (on server)
```bash
python manage.py shell
```
```python
from users.models import Department, Affiliate
merban = Affiliate.objects.get(name='Merban Capital')
depts = Department.objects.filter(affiliate=merban).order_by('name')
print(f"Total: {depts.count()} departments")
for dept in depts:
    print(f"✓ {dept.name}")
```

Expected: **11 departments** total

### 2. Via Web Application
1. Navigate to **Affiliates** page
2. Click on **Merban Capital**
3. You should now see all departments with proper names

### 3. Using Verification Script (on server)
```bash
python check_merban_departments.py
```

This will show:
- Total department count
- Each department with staff count
- Manager and HOD assignments

---

## 🔍 Why Departments Weren't Showing Before

The issue was likely:
1. **Departments didn't have the affiliate suffix** - Now they all have "(Merban Capital)"
2. **Frontend ordering array had different names** - Now updated to match
3. **Possible API mismatch** - Names now consistent between backend and frontend

---

## 🐛 Troubleshooting

### If departments still don't show after deployment:

1. **Clear browser cache:** `Ctrl + Shift + R` (hard refresh)

2. **Check API response:**
   ```bash
   # On server
   curl http://localhost:8000/api/affiliates/MERBAN_ID/departments/
   ```

3. **Verify affiliate ID in frontend:**
   - Check browser DevTools → Network tab
   - Look for the API call to `/api/affiliates/{id}/departments/`
   - Ensure correct affiliate ID is being used

4. **Check for errors:**
   ```bash
   # Backend logs
   tail -f /var/log/gunicorn/error.log
   
   # Frontend console
   # Open browser DevTools → Console tab
   ```

5. **Restart everything:**
   ```bash
   sudo systemctl restart gunicorn nginx
   cd frontend && npm run build
   ```

---

## 📝 Important Notes

### Database Safety
- ✅ All updates run in a transaction (atomic)
- ✅ If any error occurs, all changes are rolled back
- ✅ Existing staff assignments are preserved
- ✅ No data loss risk

### Staff Assignments
- All existing staff remain in their current departments
- Department names change but relationships stay intact
- The HR user in "Client Service" will automatically be in "HR & Admin (Merban Capital)"

### Manager Assignments
- Existing manager assignments are preserved
- **Action needed:** Assign managers to new departments (Audit & Compliance)

### Digital Ocean Managed Database
- The management command uses your existing Django database connection
- No need to modify database credentials
- Works with your current `settings.py` or `settings_production.py`

---

## 📊 Expected Final State

After successful deployment, Merban Capital should have **11 departments**:

1. Audit (Merban Capital) - NEW
2. Client Service/Marketing (Merban Capital)
3. Compliance (Merban Capital) - NEW
4. Corporate Finance (Merban Capital)
5. Executive (Merban Capital)
6. Finance & Accounts (Merban Capital)
7. Government Securities (Merban Capital)
8. HR & Admin (Merban Capital)
9. IT (Merban Capital)
10. Pensions & Provident Funds (Merban Capital)
11. Private Wealth & Mutual Fund (Merban Capital)

---

## 🎉 Next Steps After Deployment

1. ✅ Verify all departments show correctly in web app
2. ⚠️ Assign managers to Audit and Compliance departments
3. ⚠️ Update staff assignments if needed
4. ✅ Test leave request creation with new departments
5. ✅ Verify approval workflows work correctly

---

## 📞 Support

If you encounter any issues:
1. Check the deployment logs
2. Run the verification script
3. Review the troubleshooting section above
4. Check Django logs: `python manage.py runserver` output

---

**Ready to deploy?** Run:
```bash
git push origin main
```

Then follow the deployment steps above! 🚀
