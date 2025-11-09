import requests, os

"""Quick probe for local auth token endpoint.
Adjust EMAIL/PASSWORD via env vars HR_EMAIL / HR_PASSWORD if needed.
Falls back to hradmin@umbcapital.com / ChangeMe123! which are seeded by enhanced_reset.
Run: python quick_auth_local.py
"""

url = 'http://127.0.0.1:8000/api/auth/token/'
email = os.getenv('HR_EMAIL','hradmin@umbcapital.com')
password = os.getenv('HR_PASSWORD','ChangeMe123!')
payload = {'email': email, 'password': password}
headers={'Accept':'application/json','Content-Type':'application/json'}

try:
    r = requests.post(url, json=payload, headers=headers, timeout=10)
except Exception as e:
    print('request-error', e)
    raise SystemExit(1)

print('email-used', email)
print('status', r.status_code)
print('content-type', r.headers.get('Content-Type'))
print('body-start', r.text[:200].replace('\n',' '))
try:
    data = r.json()
    print('json-keys', list(data.keys()))
    if 'access' in data:
        print('SUCCESS: received tokens')
    else:
        print('NO_TOKENS_IN_RESPONSE')
except Exception as e:
    print('json-error', e)
