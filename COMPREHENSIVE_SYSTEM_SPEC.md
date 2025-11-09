# Leave Management System – Comprehensive Functional & Developer Specification

Version: 2025-11-09

This single document captures how the company expects the software to work, how each user persona operates (grouped by the 9 seeded users), and how the system components interrelate. It is derived from the live codebase and current production behavior, not just prior docs.

## Contents

- System goals and scope
- Architecture overview (backend, frontend, data, deployment)
- Data model and relationships
- Approval workflows and routing rules (Merban vs SDSL/SBL)
- Role personas (the 9 seeded users) and their capabilities
- Cross‑affiliate visibility and segregation rules
- Pages/UI map and what each role sees
- API surfaces used by the UI (high level)
- Notifications and audit
- Operational scripts and maintenance tasks
- Configuration & environment flags
- Edge cases and data integrity

---

## 1) System goals and scope

The system streamlines employee leave from request to final approval with a multi‑stage workflow and strict role- and affiliate-based visibility. Core goals:
- Employees can request leave, see balances, track status.
- Managers/HODs review team requests.
- HR runs policy checks and analytics; in Merban flow HR is intermediate, in SDSL/SBL flow HR is final.
- CEOs provide executive approval at the appropriate stage; each CEO only sees requests from their affiliate.
- Admin/Superuser can audit and operate the system globally.

Success criteria:
- Requests follow the correct stage progression per affiliate.
- Each role’s queue contains only requests they are allowed to act on.
- No cross‑affiliate leaks to CEOs; HR is centralized.
- Balances and histories remain consistent.

---

## 2) Architecture overview

- Backend: Django 5.x + Django REST Framework (DRF), JWT auth (SimpleJWT).
- Frontend: React (CRA) consuming the DRF API (Axios client). The frontend uses REACT_APP_API_URL to target the API directly.
- Data: MySQL in production; SQLite allowed in local dev. ORM via Django.
- Deployment: DigitalOcean; Gunicorn/WSGI behind Nginx (or App Platform as configured). Environment-driven settings.

Key backend modules:
- `users.models`: CustomUser, Department, Affiliate, EmploymentGrade (roles and org graph)
- `leaves.models`: LeaveType, LeaveRequest, LeaveBalance, LeavePolicy
- `leaves.services`: Strategy/Factory approval workflow and routing (Merban vs SDSL/SBL)
- `leaves.views`: Role-aware endpoints for lists, actions, dashboards
- `notifications`: Notification services and readiness checks

---

## 3) Data model and relationships (what developers must preserve)

- Affiliate
  - name (unique): e.g., Merban Capital, SDSL, SBL
  - Departments belong to an Affiliate. Users may belong directly to an Affiliate and optionally a Department (Merban only requires departments for non‑CEO/non‑admin roles).

- Department
  - Optional Affiliate link; Merban departments are under Merban. Holds `hod` (manager) and an `approval_flow` hint for UI.

- CustomUser (extends Django’s AbstractUser)
  - role (choices): junior_staff, senior_staff, manager (HOD), hr, ceo, admin
  - affiliate (required except for superuser; for Merban, department affiliate must be Merban)
  - department (Merban users except CEO/admin should have one; SDSL/SBL staff generally do not)
  - manager (optional; used for Merban staff)
  - grade (EmploymentGrade; used for entitlements)

- LeaveType
  - name, max days, optional certificate flag

- LeaveRequest
  - employee, leave_type, date range, total/calculated working days
 
 - Employees can request leave, see balances, track status.
 - Managers/HODs review team requests.
 - HR runs policy checks and analytics; in Merban flow HR is intermediate, in SDSL/SBL flow HR is final.
 - CEOs provide executive approval at the appropriate stage; each CEO only sees requests from their affiliate.
 - Admin/Superuser can audit and operate the system globally.

Integrity rules (from models):
 
 - Requests follow the correct stage progression per affiliate.
 - Each role’s queue contains only requests they are allowed to act on.
 - No cross‑affiliate leaks to CEOs; HR is centralized.
 - Balances and histories remain consistent.

## 4) Approval workflows and routing rules

Workflows are implemented via `leaves.services` using a Strategy/Factory pattern.
 
 - `users.models`: CustomUser, Department, Affiliate, EmploymentGrade (roles and org graph)
 - `leaves.models`: LeaveType, LeaveRequest, LeaveBalance, LeavePolicy
 - `leaves.services`: Strategy/Factory approval workflow and routing (Merban vs SDSL/SBL)
 - `leaves.views`: Role-aware endpoints for lists, actions, dashboards
 - `notifications`: Notification services and readiness checks
- Next approvers are derived from employee relationships (manager/HOD) and role queries (HR, CEO).

 
 - Non‑superuser users must have an affiliate. For Merban, non‑CEO/non‑admin must belong to a Merban department whose affiliate is Merban.
 - For SDSL/SBL, department/manager are generally cleared to avoid manager-stage routing.
- No Manager/HOD stage.

4.3 CEO routing (who is “the” CEO for a given employee)
- Determined by `ApprovalRoutingService.get_ceo_for_employee(employee)` (strict logic):
 
 - Default staff: Manager → HR → CEO (final). Status path: pending → manager_approved → hr_approved → approved (by CEO step).
 - Manager/HOD as employee: skips Manager stage; HR → CEO.
 - HR as employee: skips Manager and HR; goes directly to CEO.
 - Next approvers are derived from employee relationships (manager/HOD) and role queries (HR, CEO).
  - Missing/Unassigned affiliate → no CEO (request will remain invisible to any CEO until data is corrected).

 
 - CEO first, then HR final. Status path: pending → ceo_approved → approved (by HR step).
 - No Manager/HOD stage.
  - Admin/superuser can always approve (forops-only; not a typical business path).
  - The user’s role must match the required stage role for the request’s current status.

---

## 5) Personas – the 9 seeded users and what they can do

 
 - Determined by `ApprovalRoutingService.get_ceo_for_employee(employee)` (strict logic):
   - Employees under Merban (or in a Merban department) → Merban CEO.
   - SDSL staff → SDSL CEO.
   - SBL staff → SBL CEO.
   - CEOs are matched by affiliate name (case-insensitive with synonyms for Merban/Merban Capital).
   - Missing/Unassigned affiliate → no CEO (request will remain invisible to any CEO until data is corrected).
Below are the nine standard demo/production personas the company relies on for validation, grouped by affiliate and role. A tenth operator persona (Admin/Superuser) is also described for completeness.

1. Merban CEO (role: ceo, affiliate: Merban)
   - Sees CEO queue of Merban requests at stage hr_approved (Merban flow) and can give final approval or reject.
   - Does NOT see SDSL/SBL staff requests.
 
 - Centralized check: `ApprovalWorkflowService.can_user_approve(leave_request, user)` delegates to scenario handler `can_approve()` which enforces:
   - Admin/superuser can always approve (forops-only; not a typical business path).
   - The user’s role must match the required stage role for the request’s current status.
   - If required role is CEO, the user must be the correct CEO for the employee’s affiliate.
   - Can review categorized CEO approvals where the backend filters only approvable requests for this CEO.

2. Merban HR (role: hr, affiliate: Merban)
   - Sees HR queue:
     - Merban staff after Manager approval (manager_approved).
     - SDSL/SBL staff after CEO approval (ceo_approved) for finalization.
   - Can approve (forward to CEO for Merban, or finalize SDSL/SBL) or reject with reason.
   - Organization‑wide HR views, role summaries and user lists; can adjust entitlements by role where enabled.

3. Merban Manager/HOD (role: manager, affiliate: Merban, department required)
 
 1. Merban CEO (role: ceo, affiliate: Merban)
    - Sees CEO queue of Merban requests at stage hr_approved (Merban flow) and can give final approval or reject.
    - Does NOT see SDSL/SBL staff requests.
    - Can review categorized CEO approvals where the backend filters only approvable requests for this CEO.
   - Sees pending team requests for their department/staff they manage.
   - Can approve (forward to HR) or reject with reason.
   - Does not interact with SDSL/SBL requests.

4. Merban Senior Staff (role: senior_staff, affiliate: Merban, department required)
   - Can submit requests, view balances/history, see statuses and notifications.
   - Cannot approve others.
 
 2. Merban HR (role: hr, affiliate: Merban)
    - Sees HR queue:
      - Merban staff after Manager approval (manager_approved).
      - SDSL/SBL staff after CEO approval (ceo_approved) for finalization.
    - Can approve (forward to CEO for Merban, or finalize SDSL/SBL) or reject with reason.
    - Organization‑wide HR views, role summaries and user lists; can adjust entitlements by role where enabled.

5. Merban Junior Staff (role: junior_staff, affiliate: Merban, department required)
   - Same as Senior Staff but with potentially different default entitlements.

SDSL (2 personas)
 
 3. Merban Manager/HOD (role: manager, affiliate: Merban, department required)
    - Sees pending team requests for their department/staff they manage.
    - Can approve (forward to HR) or reject with reason.
    - Does not interact with SDSL/SBL requests.
6. SDSL CEO (role: ceo, affiliate: SDSL)
   - Sees CEO-first queue of SDSL staff requests at status pending.
   - Approve pushes to ceo_approved; HR will then finalize to approved.
   - Cannot see Merban or SBL requests.
 
 4. Merban Senior Staff (role: senior_staff, affiliate: Merban, department required)
    - Can submit requests, view balances/history, see statuses and notifications.
    - Cannot approve others.

7. SDSL Staff (role: senior_staff, affiliate: SDSL)
   - Can submit leave; no manager stage. Status moves to CEO (SDSL) directly.
 
 5. Merban Junior Staff (role: junior_staff, affiliate: Merban, department required)
    - Same as Senior Staff but with potentially different default entitlements.
   - Can view own history/balances.

SBL (2 personas)
8. SBL CEO (role: ceo, affiliate: SBL)
   - Identical to SDSL CEO, for SBL affiliate.

 
 6. SDSL CEO (role: ceo, affiliate: SDSL)
    - Sees CEO-first queue of SDSL staff requests at status pending.
    - Approve pushes to ceo_approved; HR will then finalize to approved.
    - Cannot see Merban or SBL requests.
9. SBL Staff (role: senior_staff, affiliate: SBL)
   - Identical to SDSL Staff, for SBL affiliate.

Operator (not counted in the 9 but important)
 
 7. SDSL Staff (role: senior_staff, affiliate: SDSL)
    - Can submit leave; no manager stage. Status moves to CEO (SDSL) directly.
    - Can view own history/balances.
- Admin (role: admin) and/or Superuser
  - Full visibility for audit, troubleshooting, and exceptional approvals/rejections.
  - Should not be used for normal business approvals; reserved for operations.

 
 8. SBL CEO (role: ceo, affiliate: SBL)
    - Identical to SDSL CEO, for SBL affiliate.
---

## 6) Cross‑affiliate visibility rules (what each role can see)
 
 9. SBL Staff (role: senior_staff, affiliate: SBL)
    - Identical to SDSL Staff, for SBL affiliate.

- Manager/HOD (Merban): Only requests from their managed staff/department within Merban.
  - Merban: after manager approval.
  - SDSL/SBL: after CEO approval, for finalization.
 
 - Admin (role: admin) and/or Superuser
   - Full visibility for audit, troubleshooting, and exceptional approvals/rejections.
   - Should not be used for normal business approvals; reserved for operations.
- CEO: Only requests for their own affiliate at the appropriate stage.

Data segregation guardrails:
- CEO checks are enforced server‑side in `ApprovalWorkflowService.can_user_approve` with affiliate routing.
- Views use the service layer for filtering, avoiding brittle string comparisons.
 
 - POST `/api/auth/token/`    → obtain access/refresh
 - POST `/api/auth/token/refresh/`

## 7) Pages/UI map
 
 - `/api/leaves/requests/` CRUD for the requester; server filters by role when listing.
 - `/api/leaves/manager/` manager & approvals endpoints (pending_approvals, approve, reject, approval_counts, CEO categorized where applicable).
 - `/api/leaves/types/`, `/api/leaves/balances/` for reference and balances.
 - `/api/leaves/approval-dashboard/` summary for dashboards.
- Submit Leave Request (form with type, dates, reason)
- My Requests (history, filters by status/type/date)
 
 - `users: enhanced_reset, setup_departments, assign_hods, assign_affiliate_ceos, ensure_executive_and_ceos, enforce_user_integrity, setup_production_data, set_user_password, show_users, list_users`

Role‑specific pages
 
 - `leaves: setup_leave_types, setup_production_leave_data, create_test_data, ensure_leave_balances, inspect_leave, debug_leave_request, debug_balances, fix_production_data`
- HR: HR Queue; Role/Entitlements (where enabled); Users & Departments admin; Reports/Analytics; Role Summary.
- CEO: CEO Approvals (categorized queue); Executive Dashboard/Analytics.
- Admin: Global dashboards; audit logs; operational settings.

Interrelation
- Submission creates a LeaveRequest with computed working days.
- Actions on approval pages call the DRF endpoints that change status and record approver/date/comments.
- Dashboards summarize counts pulled from the same filtered querysets.

---

## 8) API surfaces (high level)

Base prefix: `/api/` (JWT protected beyond auth endpoints)

Authentication
- POST `/api/auth/token/`    → obtain access/refresh
- POST `/api/auth/token/refresh/`

Leaves
- `/api/leaves/requests/` CRUD for the requester; server filters by role when listing.
- `/api/leaves/manager/` manager & approvals endpoints (pending_approvals, approve, reject, approval_counts, CEO categorized where applicable).
- `/api/leaves/types/`, `/api/leaves/balances/` for reference and balances.
- `/api/leaves/approval-dashboard/` summary for dashboards.

Users
- Role choices and summaries; HR/admin scoped endpoints for user/role/department views.

Note: Role and affiliate-based filtering is enforced on the backend—clients cannot broaden scope by parameters.

---

## 9) Notifications & audit

- Triggered on submission and each stage transition; targeted recipients:
  - Manager/HOD for team submissions (Merban).
  - HR on progression from Manager (Merban) and from CEO (SDSL/SBL).
  - CEO for Merban hr_approved and for SDSL/SBL pending.
- Admin can view audit trails via operations dashboards/logs.

---

## 10) Operational scripts and maintenance tasks (selected)

User & org integrity
- `users: enhanced_reset, setup_departments, assign_hods, assign_affiliate_ceos, ensure_executive_and_ceos, enforce_user_integrity, setup_production_data, set_user_password, show_users, list_users`

Leaves & data
- `leaves: setup_leave_types, setup_production_leave_data, create_test_data, ensure_leave_balances, inspect_leave, debug_leave_request, debug_balances, fix_production_data`

Diagnostics
- `leaves: diagnose_routing` – prints who can approve what and why (affiliate/role checks)
- Users/notifications readiness checks

Use these under `python manage.py <command>` with appropriate production env and safety.

---

## 11) Configuration & environment flags

- (Removed) Previous temporary flag for CEO fallback has been deprecated; routing is now always strict.
- Frontend: `REACT_APP_API_URL` to force API base URL and bypass local dev proxy when needed.
- Standard Django settings: `DEBUG`, `ALLOWED_HOSTS`, database DSN, SECRET_KEY, CORS, etc.

---

## 12) Edge cases and data integrity expectations

- Missing affiliate on users (non‑superuser): invalid; fix user records.
- Merban non‑CEO/non‑admin must have a Merban department; department’s affiliate must be Merban.
- SDSL/SBL staff shouldn’t carry departments/managers (prevents unintended manager routing).
- Approvals out of order are blocked by `can_user_approve` and status checks; admin/superuser overrides exist for operations only.
- Requests exclude admin users from staff lists and queues.

---

## 13) What a developer should verify for each persona (quick checklist)

Merban CEO
- Sees only Merban hr_approved; can approve to approved or reject.

Merban HR
- Sees Merban manager_approved and SDSL/SBL ceo_approved; can forward (Merban) or finalize (SDSL/SBL).

Merban Manager/HOD
- Sees own team pending; can approve to manager_approved or reject.

Merban Senior/Junior Staff
- Can submit, see balances/history; cannot approve.

SDSL/SBL CEO
- Sees own affiliate pending; approves to ceo_approved.

SDSL/SBL Staff
- Can submit; first approver is affiliate CEO.

Admin/Superuser (ops)
- Has global visibility for diagnosis; not a normal approver in business SOPs.

---

## 14) Known production behaviors to preserve

- CEO routing is permanently strict: requests without a resolvable affiliate do not appear in any CEO queue. Data cleanup must fix affiliate assignments rather than relying on a fallback.
- CEO queues and categorized endpoints rely on `ApprovalWorkflowService.can_user_approve`—do not reintroduce brittle string comparisons in views.

---

This specification is intended to be the authoritative reference for both functional stakeholders and developers. If a discrepancy arises between UI expectations and the rules here, align code and docs to the routing and workflow definitions in `leaves.services` and the integrity rules in `users.models`.
