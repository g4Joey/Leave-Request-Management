import os
import sys
from pathlib import Path
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_management.settings')
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import django
django.setup()

from users.models import Affiliate
from users.serializers import AffiliateSerializer


aff = Affiliate.objects.filter(name__iexact='MERBAN CAPITAL').first()
if not aff:
    print('MERBAN CAPITAL not found')
else:
    data = AffiliateSerializer(aff).data
    print(data)
