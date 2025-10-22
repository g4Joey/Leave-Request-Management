# Production Deployment Guide for DigitalOcean

## 🚀 CEO Setup for Production

You have **3 options** to create the CEO user in production:

### **Option 1: Management Command (Recommended)**
```bash
# SSH into your DigitalOcean droplet
ssh root@your-server-ip

# Navigate to your project
cd /path/to/your/django/project

# Activate virtual environment (if using one)
source venv/bin/activate  # or whatever your venv path is

# Apply migrations first
python manage.py migrate

# Create CEO with production credentials
python manage.py create_ceo \
    --username "your_actual_ceo_username" \
    --email "ceo@yourcompany.com" \
    --first-name "John" \
    --last_name "Smith" \
    --employee-id "CEO001"

# The command will output:
# ✅ Successfully created CEO user:
#    Username: your_actual_ceo_username
#    Email: ceo@yourcompany.com
#    Employee ID: CEO001
#    Default Password: ChangeMe123!
#    Role: ceo
#    Department: Executive
```

### **Option 2: Use Extended Seeding Script**
We've extended your existing `seed_demo_data.py` to include the CEO:

```bash
# This will create all demo users INCLUDING the CEO
python manage.py seed_demo_data

# CEO will be created with:
# Username: ceo@company.com
# Password: password123
# Role: ceo
# Department: Executive
```

### **Option 3: Add to JSON Seed File**
Add CEO to your `local/seed_users.json`:

```json
[
  {
    "username": "jmankoe",
    "first_name": "Ato", 
    "last_name": "Mankoe",
    "email": "jmankoe@umbcapital.com",
    "role": "manager",
    "department": "IT", 
    "password": "Atokwamena"
  },
  {
    "username": "your_ceo_username",
    "first_name": "CEO_First_Name",
    "last_name": "CEO_Last_Name", 
    "email": "ceo@umbcapital.com",
    "role": "ceo",
    "department": "Executive",
    "password": "CEO_SECURE_PASSWORD"
  }
]
```

## 🔧 Complete DigitalOcean Deployment Steps

### **1. Pre-Deployment (Local)**
```bash
# Ensure all changes are committed and pushed
git add .
git commit -m "Production deployment ready"
git push origin main
```

### **2. DigitalOcean Server Setup**
```bash
# SSH into your server
ssh root@your-server-ip

# Pull latest changes
cd /path/to/your/project
git pull origin main

# Install/update dependencies
pip install -r requirements.txt

# Apply migrations (includes CEO-related changes)
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput
```

### **3. Create CEO User**
Choose one of the 3 options above. **Option 1 (Management Command)** is recommended for production.

### **4. Verification**
```bash
# Verify the three-tier system is working
python verify_three_tier_system.py

# Should show:
# ✅ CEO User: your_ceo_username (CEO Full Name)
# ✅ CEO role available: CEO  
# ✅ Status choices updated
# ✅ All approval fields and methods working
```

### **5. Test the Workflow**
```bash
# Optional: Run workflow test
python test_approval_workflow.py

# This will test:
# Staff → Manager → HR → CEO approval chain
# Notification system
# Role-based access control
```

### **6. Restart Services**
```bash
# Restart your Django application (method depends on your setup)

# If using systemd:
sudo systemctl restart your-django-app

# If using Docker:
docker-compose restart

# If using pm2:
pm2 restart your-app

# If using gunicorn directly:
pkill gunicorn
gunicorn --bind 0.0.0.0:8000 leave_management.wsgi:application --daemon
```

## 🔐 Security Considerations for Production

### **Change Default Passwords**
```bash
# After creating CEO user, log into Django admin or use shell to change password
python manage.py shell

>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> ceo = User.objects.get(role='ceo')
>>> ceo.set_password('VERY_SECURE_PASSWORD_HERE')
>>> ceo.save()
>>> exit()
```

### **Environment Variables**
Make sure your production settings use secure credentials:

```bash
# In your .env or environment variables
CEO_USERNAME=your_actual_ceo_username
CEO_EMAIL=ceo@yourcompany.com
CEO_FIRST_NAME=John
CEO_LAST_NAME=Smith
```

## 📊 Post-Deployment Verification

### **Check CEO User Exists**
```bash
python manage.py shell

>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> ceo = User.objects.filter(role='ceo')
>>> print(f"CEO users: {ceo.count()}")
>>> for user in ceo:
...     print(f"- {user.username} ({user.get_full_name()})")
```

### **Verify Approval Workflow**
1. **Login to frontend** with a staff account
2. **Create a leave request**
3. **Login as manager** and approve it
4. **Login as HR** and approve it  
5. **Login as CEO** and give final approval
6. **Check notifications** are being sent correctly

### **API Testing**
```bash
# Test the approval dashboard endpoint
curl -H "Authorization: Token YOUR_CEO_TOKEN" \
     http://your-domain.com/api/leaves/approval-dashboard/

# Should return approval statistics and pending counts
```

## 🎯 Recommended Production Approach

**For production, I recommend:**

1. **Use Option 1 (Management Command)** with real CEO credentials
2. **Change the default password immediately** 
3. **Set up proper email notifications** (configure SMTP settings)
4. **Test the complete workflow** before going live
5. **Document the CEO credentials** securely for your team

The CEO user will have:
- ✅ Access to final approval stage
- ✅ Dashboard showing pending CEO approvals  
- ✅ Ability to reject at final stage (notifies everyone)
- ✅ Complete audit trail of their approvals
- ✅ Staff-level Django admin access

Your three-tier approval system is **production-ready** and will work seamlessly on DigitalOcean! 🎉