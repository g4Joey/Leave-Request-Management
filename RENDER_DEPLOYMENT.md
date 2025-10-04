# Render Deployment Guide

## Quick Deploy to Render

### 1. Prepare Your Repository
First, commit and push all the new Render configuration files:

```bash
git add .
git commit -m "Add Render deployment configuration"
git push origin main
```

### 2. Deploy on Render

#### Option A: Using render.yaml (Recommended)
1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New" → "Blueprint"
3. Connect your GitHub repository: `g4Joey/Leave-Request-Management`
4. Render will automatically detect the `render.yaml` file
5. Click "Apply" to deploy both services

#### Option B: Manual Setup
If Blueprint doesn't work, create services manually:

**Backend Service:**
1. New → Web Service
2. Connect GitHub repo: `g4Joey/Leave-Request-Management`
3. Configure:
   - **Name**: `leave-management-backend`
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements-render.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - **Start Command**: `gunicorn leave_management.wsgi:application`
   - **Plan**: Free

**Database:**
1. New → PostgreSQL
2. Configure:
   - **Name**: `leave-management-db`
   - **Plan**: Free

**Environment Variables for Backend:**
- `DJANGO_SETTINGS_MODULE` = `leave_management.settings_render`
- `DEBUG` = `False`
- `ALLOWED_HOSTS` = `.onrender.com`
- `DATABASE_URL` = (Auto-populated from database)
- `SECRET_KEY` = (Auto-generate)
- `CORS_ALLOWED_ORIGINS` = `https://your-frontend-url.onrender.com`

### 3. Frontend Deployment

**Option 1: Static Site on Render**
1. New → Static Site
2. Connect GitHub repo
3. Configure:
   - **Build Command**: `cd frontend && npm ci && npm run build`
   - **Publish Directory**: `frontend/build`

**Option 2: Separate Frontend Repository (Recommended)**
For better performance, you might want to deploy the frontend separately.

### 4. Update CORS Settings
After both services are deployed:
1. Update the backend's `CORS_ALLOWED_ORIGINS` environment variable
2. Add your frontend URL: `https://your-frontend-name.onrender.com`

### 5. Environment Variables Reference

**Backend Environment Variables:**
```
DJANGO_SETTINGS_MODULE=leave_management.settings_render
DEBUG=False
ALLOWED_HOSTS=.onrender.com
DATABASE_URL=(auto-populated)
SECRET_KEY=(auto-generate)
CORS_ALLOWED_ORIGINS=https://your-frontend-url.onrender.com
```

### 6. Post-Deployment Steps

1. **Create Superuser** (via Render Console):
   ```bash
   python manage.py createsuperuser
   ```

2. **Setup Demo Data** (optional):
   ```bash
   python manage.py setup_departments
   python manage.py setup_production_data
   ```

3. **Test the Deployment**:
   - Backend health: `https://your-backend.onrender.com/api/health/`
   - Admin panel: `https://your-backend.onrender.com/admin/`
   - Frontend: `https://your-frontend.onrender.com`

### 7. Troubleshooting

**Common Issues:**
- **502 Bad Gateway**: Check build logs, usually missing dependencies
- **Database Connection**: Ensure DATABASE_URL is properly set
- **CORS Errors**: Update CORS_ALLOWED_ORIGINS with correct frontend URL
- **Static Files**: Ensure collectstatic runs during build

**Check Logs:**
- Go to your service in Render Dashboard
- Click "Logs" tab to see build and runtime logs

### 8. Free Tier Limitations

**Render Free Tier:**
- Services sleep after 15 minutes of inactivity
- 750 hours/month compute time
- PostgreSQL: 1GB storage, 1GB bandwidth
- Cold starts may take 10-30 seconds

### 9. Production Considerations

For production use, consider:
- Upgrading to paid tiers for better performance
- Setting up Redis for caching
- Configuring proper domain names
- Setting up monitoring and alerts
- Regular database backups

## Files Created for Render Deployment

- `render.yaml` - Render Blueprint configuration
- `requirements-render.txt` - Python dependencies for Render
- `leave_management/settings_render.py` - Production settings for Render

## Next Steps

1. Push these files to GitHub
2. Deploy using Render Blueprint
3. Configure environment variables
4. Test the deployment
5. Set up your domain (optional)

Your Leave Management System will be live at:
- Backend: `https://leave-management-backend.onrender.com`
- Frontend: `https://leave-management-frontend.onrender.com` (if deployed separately)