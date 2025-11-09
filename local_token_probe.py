import json, sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

url = 'http://localhost:8000/api/auth/token/'
payload = {
    'username': 'hradmin@umbcapital.com',
    'password': 'ChangeMe123!'
}

data = json.dumps(payload).encode('utf-8')
req = Request(url, data=data, headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
try:
    with urlopen(req) as resp:
        ct = resp.headers.get('Content-Type')
        body = resp.read().decode('utf-8')
        print('STATUS', resp.status)
        print('CTYPE', ct)
        print('BODY', body[:200])
except HTTPError as e:
    print('ERROR', e.code, e.reason)
    try:
        print('BODY', e.read().decode('utf-8')[:400])
    except Exception:
        pass
    sys.exit(1)
except URLError as e:
    print('NETWORK_ERROR', e.reason)
    sys.exit(2)
