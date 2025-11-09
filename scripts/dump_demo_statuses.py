from leaves.models import LeaveRequest
import json

def dump(email):
    qs = LeaveRequest.objects.filter(employee__email__iexact=email).values('id','status','employee__email')
    return list(qs)

def run():
    data = {
        'merban': dump('aakorfu@umbcapital.com'),
        'sdsl': dump('asanunu@umbcapital.com'),
        'sbl': dump('staff@sbl.com'),
    }
    print(json.dumps(data, indent=2))

if __name__ == '__main__':
    run()
