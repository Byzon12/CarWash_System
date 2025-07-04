from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import StaffProfile, Staff

# Staff authentication class
class StaffAuthentication(JWTAuthentication):
    """ 
    Custom authentication class for staff authentication.
    It checks if the user is a staff member and raises an error if not.
    """
    def get_user(self, validated_token):
        try:
            user_id = validated_token['user_id']
            user = Staff.objects.get(id=user_id)
        except (KeyError, Staff.DoesNotExist):
            return None
        return user

      
