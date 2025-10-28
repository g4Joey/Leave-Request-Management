# Demo Data Reset Guide

## Overview
The demo data reset feature allows you to reset all leave requests and balances before a CEO demo or presentation, while preserving all user accounts, departments, and entitlements.

## What Gets Reset
✅ **Deleted:**
- All leave requests (approved, pending, rejected)

✅ **Reset to Zero:**
- All leave balances: `used_days = 0`, `pending_days = 0`

✅ **Preserved:**
- All user accounts (employees, managers, HR, CEOs)
- All departments and affiliates
- All leave types and entitlements (`entitled_days`)
- All system configurations

---

## Usage Methods

### Method 1: Environment Variable (Recommended for Production)

**When to use:** Before a scheduled demo on your production server

**Steps:**

1. **Set the environment variable in your deployment platform:**
   
   **DigitalOcean App Platform:**
   - Go to your app → Settings → Environment Variables
   - Add: `RUN_RESET_DEMO_DATA = 1`
   - Save changes

   **Docker Compose:**
   ```yaml
   environment:
     - RUN_RESET_DEMO_DATA=1
   ```

   **Manual Export:**
   ```bash
   export RUN_RESET_DEMO_DATA=1
   ```

2. **Trigger a redeploy:**
   - DigitalOcean: Click "Deploy" or push to GitHub
   - Docker: Run `docker-compose down && docker-compose up`
   - Manual: Restart your application

3. **The reset will run automatically on startup**
   - Check deployment logs to confirm: "Demo data reset complete"

4. **⚠️ IMPORTANT: Disable the trigger immediately after deployment:**
   - Change `RUN_RESET_DEMO_DATA = 0` (or delete the variable)
   - This prevents the reset from running on every subsequent deployment

---

### Method 2: Manual Script Execution (Local/Testing)

**When to use:** Testing locally or one-time manual reset

**Steps:**

1. **Navigate to project directory:**
   ```bash
   cd "d:\Desktop\Leave management"
   ```

2. **Run the reset script:**
   ```bash
   python reset_demo_data.py
   ```

3. **Confirm the action:**
   - Type exactly: `RESET DEMO DATA`
   - Press Enter

4. **Verify the output:**
   ```
   ✅ Deleted X leave requests
   ✅ Reset Y leave balances to zero
   🎯 System is now ready for CEO demo!
   ```

---

## Safety Features

🔒 **Transaction-safe:** If any error occurs, all changes are rolled back

🔒 **Confirmation required:** Interactive mode requires exact text confirmation

🔒 **Logging:** All operations are logged with counts and timestamps

🔒 **No data loss:** User accounts and entitlements are never deleted

---

## Typical Demo Workflow

1. **One day before demo:**
   - Set `RUN_RESET_DEMO_DATA=1` in production
   - Trigger redeploy
   - Verify in logs: "Demo data reset complete"
   - **SET `RUN_RESET_DEMO_DATA=0` immediately**

2. **Demo day:**
   - System shows clean slate: all users have full leave balances
   - No historical leave requests clutter the interface
   - CEOs can create test leave requests without confusion

3. **After demo:**
   - Keep the clean state, or restore from backup if needed
   - Continue normal operations

---

## Troubleshooting

**Issue:** Reset runs on every deployment

**Solution:** You forgot to set `RUN_RESET_DEMO_DATA=0`. Update the environment variable immediately.

---

**Issue:** Script fails with database errors

**Solution:** Check database connection in deployment logs. The script uses Django transactions and will rollback on errors.

---

**Issue:** Environment variable not detected

**Solution:** 
- Ensure exact spelling: `RUN_RESET_DEMO_DATA` (case-sensitive)
- Value must be exactly `1` (not `true`, `yes`, or anything else)
- Restart/redeploy after setting the variable

---

## Example: DigitalOcean Setup

### Setting the Variable

1. Go to: https://cloud.digitalocean.com/apps
2. Select your Leave Management app
3. Navigate to: **Settings** → **App-Level Environment Variables**
4. Click: **Edit**
5. Add variable:
   - Key: `RUN_RESET_DEMO_DATA`
   - Value: `1`
   - Scope: All components
6. Click: **Save**
7. Click: **Deploy** (or push to GitHub to trigger auto-deploy)

### Disabling After Reset

1. Return to: **Settings** → **App-Level Environment Variables**
2. Find: `RUN_RESET_DEMO_DATA`
3. Edit value from `1` to `0` (or delete the variable)
4. Click: **Save**
5. No need to redeploy unless you want to verify

---

## Security Considerations

- Only HR and Admin users should have access to deployment settings
- Consider using a more complex trigger value for production (e.g., a UUID)
- Always disable the trigger immediately after use
- Keep backups before running resets in production

---

## Contact

For issues or questions about the demo reset feature, contact your system administrator.
