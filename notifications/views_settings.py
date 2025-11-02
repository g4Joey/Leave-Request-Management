from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import SiteSetting

class OverlapSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Only admin/superuser can view settings
        user = request.user
        if not (getattr(user, 'role', '') == 'admin' or user.is_superuser):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        
        def get_value(key, default):
            obj = SiteSetting.objects.filter(key=key).first()
            return obj.value if obj and obj.value != '' else str(default)
        
        data = {
            "min_days": int(get_value('OVERLAP_NOTIFY_MIN_DAYS', 2)),
            "min_count": int(get_value('OVERLAP_NOTIFY_MIN_COUNT', 2)),
            "enabled": get_value('OVERLAP_DETECT_ENABLED', True) in ['1','true','yes','on','True','YES','ON'],
            "range": {"min": 1, "max": 20}
        }
        return Response(data)

    def put(self, request):
        user = request.user
        if not (getattr(user, 'role', '') == 'admin' or user.is_superuser):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        
        min_days = request.data.get('min_days')
        enabled = request.data.get('enabled')
        # Optionally accept min_count too, but focus is the slider for min_days
        
        try:
            if min_days is not None:
                min_days = int(min_days)
                # Clamp to 1-20
                if min_days < 1: min_days = 1
                if min_days > 20: min_days = 20
                SiteSetting.objects.update_or_create(key='OVERLAP_NOTIFY_MIN_DAYS', defaults={'value': str(min_days)})
            
            if enabled is not None:
                enabled_str = 'true' if str(enabled).lower() in ['1','true','yes','on'] else 'false'
                SiteSetting.objects.update_or_create(key='OVERLAP_DETECT_ENABLED', defaults={'value': enabled_str})
            
            return Response({"detail": "Settings updated"})
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
