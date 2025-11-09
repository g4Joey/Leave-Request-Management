import requests, time
for i in range(10):
    try:
        r = requests.get('http://127.0.0.1:3000', timeout=2)
        print('UP', r.status_code, r.headers.get('content-type'))
        break
    except Exception as e:
        print('DOWN', type(e).__name__)
        time.sleep(1)
else:
    print('NOT_UP')
