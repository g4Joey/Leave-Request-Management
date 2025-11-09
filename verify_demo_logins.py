import requests
URL='http://127.0.0.1:8000/api/auth/token/'
USERS=['ceo@umbcapital.com','hr@merban.com','manager@merban.com','staff@merban.com','sdslceo@umbcapital.com','staff@sdsl.com','sblceo@umbcapital.com','staff@sbl.com']
for email in USERS:
    r=requests.post(URL, json={'username':email,'password':'ChangeMe123!'}, headers={'Accept':'application/json'})
    ct=r.headers.get('content-type')
    ok=ct and ct.startswith('application/json') and 'access' in (r.json() if 'application/json' in ct else {})
    print(f"{email}: {r.status_code} {ct} {'OK' if ok else 'FAIL'}")
