import os
import time
from typing import Optional

import requests
import streamlit as st

# Simple Streamlit front-end that talks to the existing Django REST API.
# Usage: pip install -r requirements.txt (streamlit already in requirements), then:
# STREAMLIT_API_URL=http://127.0.0.1:8000/api streamlit run streamlit_app.py


def _get_default_api_url() -> str:
    return os.environ.get("STREAMLIT_API_URL", "http://127.0.0.1:8000/api")


def ensure_session():
    if "session" not in st.session_state:
        st.session_state.session = requests.Session()
    if "access" not in st.session_state:
        st.session_state.access = None
    if "refresh" not in st.session_state:
        st.session_state.refresh = None
    if "api_url" not in st.session_state:
        st.session_state.api_url = _get_default_api_url()


def auth_headers():
    if st.session_state.get("access"):
        return {"Authorization": f"Bearer {st.session_state.access}"}
    return {}


def get_full_url(path: str) -> str:
    base = st.session_state.api_url.rstrip("/")
    path = path.lstrip("/")
    return f"{base}/{path}"


def login(username: str, password: str) -> tuple[bool, str]:
    url = get_full_url("auth/token/")
    try:
        r = st.session_state.session.post(url, json={"username": username, "password": password}, timeout=10)
    except Exception as e:
        return False, f"Request error: {e}"
    if r.status_code == 200:
        tokens = r.json()
        st.session_state.access = tokens.get("access")
        st.session_state.refresh = tokens.get("refresh")
        return True, "Logged in"
    return False, f"Login failed: {r.status_code} {r.text}"


def refresh_access() -> bool:
    if not st.session_state.get("refresh"):
        return False
    url = get_full_url("auth/token/refresh/")
    try:
        r = st.session_state.session.post(url, json={"refresh": st.session_state.refresh}, timeout=10)
    except Exception:
        return False
    if r.status_code == 200:
        st.session_state.access = r.json().get("access")
        return True
    # refresh failed -- clear tokens
    st.session_state.access = None
    st.session_state.refresh = None
    return False


def api_request(method: str, path: str, retry: bool = True, **kwargs) -> Optional[requests.Response]:
    url = get_full_url(path)
    headers = kwargs.pop("headers", {})
    headers.update(auth_headers())
    try:
        resp = st.session_state.session.request(method, url, headers=headers, timeout=15, **kwargs)
    except Exception as e:
        st.error(f"Network error when calling API: {e}")
        return None
    if resp.status_code == 401 and retry:
        # Try refresh once
        ok = refresh_access()
        if ok:
            headers = auth_headers()
            try:
                resp = st.session_state.session.request(method, url, headers=headers, timeout=15, **kwargs)
            except Exception as e:
                st.error(f"Network error when calling API after refresh: {e}")
                return None
    return resp


def show_dashboard():
    st.header("Leave Management — Streamlit Dashboard")
    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("Your leave balances")
        resp = api_request("get", "leaves/balances/current_year_full/")
        if resp is None:
            st.info("No response from API — check the API URL and your network.")
        elif resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and "results" in data:
                items = data["results"]
            else:
                items = data
            if not items:
                st.info("No leave balances found for your account.")
            else:
                for b in items:
                    st.markdown(f"**{b.get('leave_type_display','Leave')}** — {b.get('entitled_days',0)} entitled, {b.get('used_days',0)} used, {b.get('remaining_days',0)} remaining")
        else:
            st.error(f"Failed to fetch balances: {resp.status_code} - {resp.text}")

    with col2:
        st.subheader("Recent leave requests")
        resp = api_request("get", "leaves/requests/?limit=10")
        if resp is None:
            st.info("No response from API — check the API URL and your network.")
        elif resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and "results" in data:
                requests_list = data["results"]
            else:
                requests_list = data
            if not requests_list:
                st.info("No recent requests")
            else:
                for r in requests_list:
                    with st.expander(f"{r.get('employee_name') or r.get('employee')}: {r.get('leave_type_display','Leave')} ({r.get('status')})"):
                        st.write(r)
                        if r.get('status') == 'pending':
                            cols = st.columns(3)
                            if cols[0].button("Approve", key=f"approve-{r['id']}"):
                                do_approve_reject(r['id'], 'approve')
                                st.experimental_rerun()
                            if cols[1].button("Reject", key=f"reject-{r['id']}"):
                                do_approve_reject(r['id'], 'reject')
                                st.experimental_rerun()
                            cols[2].write("")
        else:
            st.error(f"Failed to fetch requests: {resp.status_code} - {resp.text}")


def do_approve_reject(pk: int, action: str):
    assert action in ("approve", "reject")
    path = f"leaves/manager/{pk}/{action}/"
    payload = {"approval_comments": "Processed via Streamlit"}
    resp = api_request("put", path, json=payload)
    if resp is None:
        st.error("No response from server")
    elif resp.status_code in (200, 201, 204):
        st.success(f"Request {action}ed successfully")
    else:
        st.error(f"Failed to {action}: {resp.status_code} - {resp.text}")


def main():
    st.set_page_config(page_title="Leave Management (Streamlit)", layout="wide")
    ensure_session()

    st.sidebar.title("Configuration")
    st.session_state.api_url = st.sidebar.text_input("API base URL (example: http://127.0.0.1:8000/api)", value=st.session_state.api_url)
    st.sidebar.markdown("---")

    if not st.session_state.get("access"):
        st.sidebar.subheader("Sign in")
        username = st.sidebar.text_input("Email or username", key="username")
        password = st.sidebar.text_input("Password", type="password", key="password")
        if st.sidebar.button("Sign in"):
            ok, msg = login(username, password)
            if ok:
                st.sidebar.success("Signed in")
                # small delay to ensure session headers pick up
                time.sleep(0.2)
                st.experimental_rerun()
            else:
                st.sidebar.error(msg)
    else:
        st.sidebar.subheader("Account")
        st.sidebar.write("Signed in")
        if st.sidebar.button("Sign out"):
            st.session_state.access = None
            st.session_state.refresh = None
            st.experimental_rerun()

    # Show main dashboard
    show_dashboard()


if __name__ == "__main__":
    main()
