from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class EmailOrUsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Allow login using either username or email.
    Frontend sends { username: <email>, password }, so we resolve the email to the user's username
    before calling the parent validator.
    """

    def validate(self, attrs):
        login = attrs.get('username') or attrs.get('email')
        if login and '@' in login:
            User = get_user_model()
            try:
                user = User.objects.get(email__iexact=login)
                attrs['username'] = user.get_username()
            except User.DoesNotExist:
                # Leave as-is; parent will fail with standard error
                pass

        return super().validate(attrs)


class EmailOrUsernameTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailOrUsernameTokenObtainPairSerializer
