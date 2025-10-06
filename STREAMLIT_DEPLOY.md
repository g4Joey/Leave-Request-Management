Streamlit deployment notes for Leave Management app

Overview
--------
This repository contains a Django REST API (backend) and a React frontend. The Streamlit app provided here is a lightweight front-end wrapper that calls the existing Django REST API endpoints to display leave balances, recent leave requests and to allow managers to approve/reject requests.

Two hosting patterns
--------------------
1) Streamlit Cloud (recommended for minimal ops)
   - Run the Streamlit app on Streamlit Cloud and point it at your production Django API.
   - Set the environment variable STREAMLIT_API_URL to your API root (e.g. https://api.example.com/api)
   - Add production secrets and any API credentials to Streamlit Cloud's secret manager.

2) Self-hosted (DigitalOcean / VM / Docker)
   - Run the Django backend as usual (on a VM, Docker, or managed platform).
   - Run the Streamlit app on the same network or publicly (bind to 0.0.0.0) and set STREAMLIT_API_URL.
   - Use an HTTPS reverse proxy (nginx) if exposing the Streamlit app publicly.

Files added
-----------
- `streamlit_app.py` - Example Streamlit wrapper that authenticates with the API (JWT) and shows balances and recent requests. It also supports approving/rejecting pending requests.
- `STREAMLIT_DEPLOY.md` - This file.

How to run locally
------------------
1. Install requirements (in your Python venv):
   pip install -r requirements.txt

2. Ensure Django API is running locally at http://127.0.0.1:8000 with /api routes available.

3. Start Streamlit:
   set STREAMLIT_API_URL=http://127.0.0.1:8000/api
   streamlit run streamlit_app.py

Notes and limitations
---------------------
- This Streamlit app is intentionally small and used as a rapid UI for inspection and manager workflows. It is not a full replacement for the React frontend.
- The app uses JWT tokens obtained from `/api/auth/token/` and refreshes tokens with `/api/auth/token/refresh/`. Ensure your Django settings allow the client to use these endpoints (CORS, CSRF not required for token endpoints if using JSON).
- Approve/reject calls use the manager endpoints: `PUT /api/leaves/manager/{id}/approve/` and `PUT /api/leaves/manager/{id}/reject/`. User must have manager/HR/admin permissions.
- For production, store API URL and any secrets in the host's secret manager. Do not commit secrets to the repo.

Next steps (optional)
----------------------
- Add unit tests for the Streamlit helper functions (mocking requests.Session).
- Add a small Dockerfile to containerize the Streamlit app and publish it alongside the Django backend.
- Improve UI/UX: add pagination, filters, and per-request detailed views.
