# Leave Management System – Comprehensive Functional & Developer Specification (Clean)

Version: 2025-11-09

This document supersedes previous malformed versions. It captures expected functional behavior, seeded personas, and developer obligations.

## Contents
- System goals and scope
- Architecture overview (backend, frontend, data, deployment)
- Data model and relationships
- Approval workflows and routing rules
- Role personas (9 seeded users) + operator
- Cross‑affiliate visibility rules
- Pages/UI map
- API surfaces (high level)
- Notifications & audit
- Operational scripts
- Configuration & environment flags
- Edge cases & integrity
- Persona verification checklist
- Production behaviors to preserve

---
## 1) System goals and scope

The system streamlines employee leave from request to final approval with a multi‑stage workflow and strict role + affiliate visibility.

Core goals:
- Employees request leave, see balances, track status.
- Managers/HODs review team requests (Merban only).
- HR performs policy/intermediate or final reviews depending on affiliate flow.
- CEOs give executive approvals only for their affiliate.
- Admin/Superuser audits and operates globally (operations only).


Key backend modules:

- `users.models`: CustomUser, Department, Affiliate, EmploymentGrade.

- `leaves.models`: LeaveType, LeaveRequest, LeaveBalance, LeavePolicy.

## 3) Data model essentials

- Optional affiliate; Merban departments belong to Merban; stores `hod`.


- department (Merban non‑CEO/non‑admin required; SDSL/SBL usually none).

LeaveRequest:

- employee, leave_type, date range, computed working days, status progression.

LeaveBalance:



---





- Path: pending → manager_approved → hr_approved → approved (CEO final).

- Path: pending → ceo_approved → approved (HR final).

- No manager/HOD stage.



- SBL staff → SBL CEO.





2. Merban HR – sees manager_approved Merban + ceo_approved SDSL/SBL.

3. Merban Manager/HOD – sees pending team requests (Merban only).
4. Merban Senior Staff – submits, views history/balances.
5. Merban Junior Staff – same as senior; differing entitlements.

SDSL (2):
6. SDSL CEO – first approver (pending → ceo_approved).

7. SDSL Staff – submits; CEO first approver.

SBL (2):

8. SBL CEO – identical to SDSL CEO for SBL.
9. SBL Staff – identical to SDSL Staff for SBL.


Operator:

---


- CEO: Only own affiliate’s requests at their stage.

- Affiliate-based CEO checks in `can_user_approve`.

- Service-layer filtering for queues; avoid direct string role checks in views.

---



- Admin: Global dashboards, audit logs, operations settings.



- Approvals update status + timestamps + approver.



- POST /api/auth/token/



Leaves:

- /api/leaves/manager/ (pending_approvals, approve, reject, approval_counts)

- /api/leaves/approval-dashboard/

- Role choices, department/affiliate summaries, HR/admin scoped user management.





## 9) Notifications & audit

Events:


- Admin views logs, status histories.





- Strict CEO routing is permanent (fallback flag removed).


---
## 12) Edge cases & integrity

- Missing affiliate (non‑superuser) → fix record before approvals progress.
- Merban staff must align department affiliate.
- SDSL/SBL staff should not have manager/department to avoid extra stage.
- Out-of-order approvals rejected by status + `can_user_approve`.
- Admin overrides rarely used; log actions.

---
## 13) Persona verification checklist

- Merban CEO: sees hr_approved Merban only; approves final.
- Merban HR: sees manager_approved Merban + ceo_approved SDSL/SBL.
- Manager/HOD: sees pending team (Merban) only.
- Merban Staff: submits; sees own history/balances.
- SDSL/SBL CEO: sees pending own affiliate; approves to ceo_approved.
- SDSL/SBL Staff: submits; first approver CEO.
- Admin: global audit, diagnostic, not standard approver.

---
## 14) Production behaviors to preserve

- CEO routing strictly affiliate-bound; missing affiliate hides from CEO queues.
- Queue filtering centralized in services; no brittle role string comparisons in views.

---
This specification is authoritative. Resolve discrepancies by aligning code with `leaves.services` workflow + model integrity rules in `users.models`.
