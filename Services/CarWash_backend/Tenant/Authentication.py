from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import AuthenticationFailed
from .models import TenantProfile, Tenant


# Tenant authentication class
class TenantAuthentication(JWTAuthentication):
    """
    Custom authentication class for tenant authentication.
    It checks if the user is a tenant and raises an error if not.
    """
    def get_user(self, validated_token):
        try:
            user_id = validated_token['user_id']
            user = Tenant.objects.get(id=user_id)
        except (KeyError, Tenant.DoesNotExist):
            return None
        return user

