
# DigitalOcean Production Deployment Guide

This guide helps you deploy and troubleshoot the app on a DigitalOcean Droplet (Docker or bare-metal Gunicorn). It avoids all AWS-specific steps.

## 1) Pull latest code and install dependencies

On your Droplet:

```bash
ssh root@<your-server-ip>
cd /opt/leave-management   # or your project path
git pull origin main

# Python deps
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip wheel
pip install -r requirements.txt
```

If you use environment files, verify `.env` or exported env vars are present with correct DATABASE settings, SECRET_KEY, ALLOWED_HOSTS, etc.

## 2) Run Django migrations and static collection

```bash
source .venv/bin/activate
python manage.py migrate

# If notifications tables/settings are missing, run:
python manage.py ensure_notifications_ready

python manage.py collectstatic --noinput
```

## 3) Build frontend and publish static files

```bash
cd frontend
npm ci
npm run build
cd ..

# Re-collect to pick up new build
python manage.py collectstatic --noinput
```

Note: If you serve the built frontend from Nginx, point Nginx to `frontend/build` or ensure Django’s static root serves the built assets.

## 4) Restart services

Depending on your process manager:

- systemd (Gunicorn):

```bash
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

- Docker Compose:

```bash
docker compose pull
docker compose up -d --build
```

## 5) CEO portal expectations (production)

- SDSL/SBL CEOs: only the “Staff Requests” tab is visible.
- Merban CEO: sees HOD/Manager, HR, and Staff tabs.
- CEOs only see requests from their own affiliate.

Backend enforces this via `/api/leaves/manager/ceo_approvals_categorized/` and affiliate-aware filtering. Frontend also hides tabs based on the `ceo_affiliate` field in the API response.

## 6) Quick health checks

```bash
# Django checks
python manage.py check

# API ping (adjust domain/token)
curl -I https://<your-domain>/api/leaves/manager/approval_counts/
```

## 7) Production troubleshooting playbook

When an item “doesn’t show” or “goes to the wrong queue,” run these targeted checks.

### A) Trace a specific request

1) Get the request ID from the UI or database.
2) Call the trace endpoint as an authenticated admin/CEO/HR:

```bash
curl -H "Authorization: Bearer <ACCESS_TOKEN>" \
  https://<your-domain>/api/leaves/manager/<REQUEST_ID>/trace/
```

You’ll see: current status, handler class, affiliate, and booleans like `can_ceo_approve_now`.

Interpretation:

- SDSL/SBL flow: `pending` → CEO first; after CEO it becomes `ceo_approved` → HR final (`approved`).
- Merban flow: `pending` → Manager → `manager_approved` → HR → `hr_approved` → CEO final (`approved`).

If a legacy SDSL/SBL request shows `hr_approved` (instead of `ceo_approved`) it will not be actionable. Manually set it to `ceo_approved` (admin) and proceed, or recreate the request.

### B) Validate CEO visibility for SBL/SDSL (e.g., Esther case)

Run this diagnostic inside Django shell on the Droplet:

```bash
python manage.py shell -c "exec(open('diag_sbl_ceo_missing.py').read())"
```

It prints each pending SBL request and whether the SBL CEO can approve. If nothing prints, check that:

- The employee affiliate is actually SBL (user.affiliate or department.affiliate)
- The request status is correct for the flow (`pending` for CEO stage in SBL/SDSL)

### C) Validate Merban staff skipping manager (e.g., GSAFO case)

Run:

```bash
python manage.py shell -c "exec(open('diag_gsafo_flow.py').read())"
```

It shows the user’s department/manager and the request’s handler/flow. If the user has no manager and no department HOD, the system will auto-bypass to HR (intended). Assign a manager/HOD to enforce the manager step.

### D) Restore/verify Cancel button for pending requests

The Cancel action is available only while a request is `pending` and only to the requester. In the UI it calls:
`PUT /api/leaves/manager/<id>/cancel/`

If the button doesn’t show, confirm the status is exactly `pending` and the frontend assets are updated (see step 3). Clear the browser cache if needed.

## 8) Notes on caching

If UI tabs or buttons don’t reflect the latest logic, you’re likely seeing an old bundle. After rebuilds, hard-refresh the browser (Ctrl+F5) or clear cache. For Nginx, consider far-future caching for hashed assets only.

## 9) Safety scripts available

- `verify_three_tier_system.py` – sanity-checks core model/fields and roles.
- `verify_todays_changes.py` – validates affiliate routing, exceptions, and notifications.
- `diag_sbl_ceo_missing.py` – checks SBL pending visibility for SBL CEO.
- `diag_gsafo_flow.py` – inspects a specific user’s department/manager and latest request flow.

Run with:

```bash
python verify_todays_changes.py
python manage.py shell -c "exec(open('diag_sbl_ceo_missing.py').read())"
```

---

If you get stuck, capture the `trace` output for the affected request ID and the employee email/affiliate, and we can pinpoint the exact rule that’s gating visibility or action.
