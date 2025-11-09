import os, json, urllib.request, urllib.error

BASE = os.environ.get('PRODUCTION_BASE_URL', '').rstrip('/') or 'https://takeabreak-app-38abv.ondigitalocean.app/api'
TOKEN_URL = f"{BASE}/auth/token/"
PENDING_URL = f"{BASE}/leaves/manager/pending_approvals/?stage=ceo"
CATEG_URL = f"{BASE}/leaves/manager/ceo_approvals_categorized/"

CEO_EMAIL = os.environ.get('PRODUCTION_CEO_EMAIL')
CEO_PASSWORD = os.environ.get('PRODUCTION_CEO_PASSWORD')

if not CEO_EMAIL or not CEO_PASSWORD:
    raise SystemExit('Set PRODUCTION_CEO_EMAIL and PRODUCTION_CEO_PASSWORD env vars before running')

def post_json(url, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode('utf-8')
            return resp.getcode(), json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        return e.code, {'error':'http', 'status': e.code, 'body': body[:400]}
    except Exception as e:
        return 0, {'error':'network', 'message': str(e)}

def get_json(url, token):
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode('utf-8')
            return resp.getcode(), json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        return e.code, {'error':'http', 'status': e.code, 'body': body[:400]}
    except Exception as e:
        return 0, {'error':'network', 'message': str(e)}

# 1) Obtain CEO token
status, tok = post_json(TOKEN_URL, {'email': CEO_EMAIL, 'password': CEO_PASSWORD})
if status != 200 or 'access' not in tok:
    print('[FAIL] token obtain', status, tok)
    raise SystemExit(2)
access = tok['access']
print('[OK] Token acquired for', CEO_EMAIL)

# 2) Fetch CEO pending approvals
s1, p = get_json(PENDING_URL, access)
print('pending_approvals status:', s1)
if isinstance(p, dict):
    print('count:', p.get('count'))
    # print sample items if present
    reqs = p.get('requests') or []
    print('sample:', json.dumps(reqs[:2], indent=2))
else:
    print('payload:', str(p)[:400])

# 3) Fetch CEO categorized approvals
s2, c = get_json(CATEG_URL, access)
print('ceo_approvals_categorized status:', s2)
if isinstance(c, dict):
    print('total_count:', c.get('total_count'))
    cats = c.get('categories') or {}
    print('counts:', {k: len(v) for k,v in cats.items()})
    # sample staff items
    staff = cats.get('staff') or []
    print('staff_sample:', json.dumps(staff[:2], indent=2))
else:
    print('payload:', str(c)[:400])
