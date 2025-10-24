# 🚀 DEPLOY TO DIGITAL OCEAN - QUICK CHECKLIST

## ✅ Pre-Deployment Checklist

- [x] Management command created: `update_merban_departments.py`
- [x] Verification script created: `check_merban_departments.py`
- [x] Changes committed to git
- [ ] Changes pushed to GitHub
- [ ] Deployed to Digital Ocean

---

## 🔥 QUICK DEPLOY (3 Steps)

### Step 1: Push to GitHub
```bash
git push origin main
```

### Step 2: SSH into Digital Ocean
```bash
ssh root@YOUR_DROPLET_IP
```

### Step 3: Update & Run on Server
```bash
cd /path/to/Leave-Request-Management
git pull origin main
python manage.py update_merban_departments
sudo systemctl restart gunicorn  # Or your app server
```

---

## 📋 What Will Change

### Departments Being Renamed (8):
1. **Accounts & Compliance** → Finance & Accounts (Merban Capital)
2. **Government Securities** → Government Securities (Merban Capital)
3. **PENSIONS** → Pensions & Provident Funds (Merban Capital)
4. **IT** → IT (Merban Capital)
5. **IHL** → Client Service/Marketing (Merban Capital)
6. **Client Service** → HR & Admin (Merban Capital) *(has HR user)*
7. **STOCKBROKERS** → Private Wealth & Mutual Fund (Merban Capital)
8. **SDSL** (department) → Corporate Finance (Merban Capital)

### Departments Being Created (2):
9. **Audit (Merban Capital)** - NEW
10. **Compliance (Merban Capital)** - NEW

### Departments Unchanged (1):
- **Executive** - Kept as is (has Benjamin Ackah)

---

## 🔍 Verify After Deployment

### 1. Check via Django Shell on Server:
```bash
python manage.py shell
```
```python
from users.models import Department, Affiliate
merban = Affiliate.objects.get(name='Merban Capital')
for dept in Department.objects.filter(affiliate=merban).order_by('name'):
    print(f"✓ {dept.name} ({dept.customuser_set.count()} staff)")
```

### 2. Check via Web App:
1. Go to **Affiliates** page
2. Click on **Merban Capital**
3. You should see all 11 departments with "(Merban Capital)" suffix

---

## 🐛 If Departments Still Don't Show

### Issue: API not returning departments

**Check the API response:**
```bash
curl -X GET https://your-domain.com/api/affiliates/MERBAN_ID/departments/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Common fixes:**
1. Hard refresh browser (Ctrl + Shift + R)
2. Check network tab in DevTools for API call
3. Verify frontend is fetching from correct affiliate ID
4. Restart both backend and frontend:
   ```bash
   sudo systemctl restart gunicorn
   cd frontend && npm run build  # If using production build
   ```

### Issue: Wrong affiliate ID in frontend

Check `AffiliatePage.js` - make sure it's using the correct affiliate ID or slug to fetch departments.

---

## 📝 Commands Summary

| Action | Command |
|--------|---------|
| **Push changes** | `git push origin main` |
| **SSH to server** | `ssh root@YOUR_DROPLET_IP` |
| **Update code** | `git pull origin main` |
| **Run migration** | `python manage.py update_merban_departments` |
| **Restart app** | `sudo systemctl restart gunicorn` |
| **Verify** | `python check_merban_departments.py` |

---

## 🆘 Need Help?

**If you see "Merban Capital affiliate not found":**
- The affiliate might be named differently
- Run: `python manage.py shell -c "from users.models import Affiliate; [print(f'{a.id}: {a.name}') for a in Affiliate.objects.all()]"`

**If departments exist but don't show on web:**
- Check the affiliate ID being used in the API call
- Verify the frontend route: `/api/affiliates/{id}/departments/`
- Check browser console for errors

**If you can't SSH:**
- Use Digital Ocean console access from the web dashboard
- Or use the verification script locally (won't work but shows you the logic)

---

## ✨ After Successful Deployment

1. ✅ Verify all 11 departments show in Merban Capital
2. ✅ Assign managers to new departments (Audit & Compliance)
3. ✅ Update staff department assignments if needed
4. ✅ Test leave request creation with new departments
5. ✅ Check dashboard reflects correct department structure

---

**Created:** October 24, 2025  
**Last Updated:** {{ deployment_time }}
