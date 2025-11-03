from leaves.models import LeaveRequest
from users.models import CustomUser

hr_users = CustomUser.objects.filter(role='hr')
print(f'Found {hr_users.count()} HR users\n')

for hr in hr_users:
    print(f'HR User: {hr.username} ({hr.email})')
    print(f'  Role: {hr.role}')
    print(f'  Manager: {hr.manager}')
    print(f'  Department: {hr.department}')
    
    # Check their leave requests
    requests = LeaveRequest.objects.filter(employee=hr).order_by('-created_at')
    print(f'  Leave Requests: {requests.count()}')
    
    for lr in requests[:3]:  # Show last 3
        print(f'    - ID: {lr.id}, Status: {lr.status}, Created: {lr.created_at}')
    print()
