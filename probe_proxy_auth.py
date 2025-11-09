import requests

# Probe the dev proxy via the browser port (CRA dev server) to ensure /api forwards.
# Adjust port if CRA changed.
PORT = 3000  # fallback to 3000; update here if using 3001
url = f'http://localhost:{PORT}/api/auth/token/'
payload = {'username': 'ceo@company.com', 'password': 'CEOPassword123!'}
headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

print('Probing', url)
try:
    resp = requests.post(url, json=payload, headers=headers, timeout=10)
except Exception as e:
    print('Request error:', e)
    raise SystemExit(1)

print('status', resp.status_code)
print('ct', resp.headers.get('content-type'))
print('start', resp.text[:160].replace('\n', ' '))
try:
    data = resp.json()
    print('keys', list(data.keys())[:10])
except Exception as e:
    print('json-error', e)
