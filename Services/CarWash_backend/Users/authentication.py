from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

class UsernameOrEmailBackend(ModelBackend):
    
    def authenticate(self, request, username=None, password=None, **kwargs):
       try:
            # Attempt to get the user by username or email
            user = User.objects.get(Q(username=username) | Q(email=username))
            # Check if the password is correct and if the user can authenticate
            # Note: The user_can_authenticate method is overridden to always return True
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
       except User.DoesNotExist:
            return None
            