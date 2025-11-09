import json, urllib.request
payload = json.dumps({'username':'hradmin@umbcapital.com','password':'ChangeMe123!'}).encode()
req = urllib.request.Request('http://127.0.0.1:8000/api/auth/token/', payload, {'Content-Type':'application/json','Accept':'application/json'})
try:
    with urllib.request.urlopen(req) as r:
        body = r.read().decode()
        print('STATUS', r.status)
        print('BODY_HEAD', body[:300])
except Exception as e:
    print('ERROR', e)
