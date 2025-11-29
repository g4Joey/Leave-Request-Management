#!/usr/bin/env python
"""Simple HTTP test with requests library"""
import requests

try:
    resp = requests.get("http://127.0.0.1:8000/api/auth/login/", timeout=2)
    print(f"Server is running! Status: {resp.status_code}")
except requests.exceptions.ConnectionError:
    print("❌ Server is NOT running")
    print("Start it with: python manage.py runserver")
except Exception as e:
    print(f"Error: {e}")
