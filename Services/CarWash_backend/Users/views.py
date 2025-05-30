from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from .serializer import UserSerializer



class RegisterUserView(generics.CreateAPIView):
    """
    View to register a new user.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]  # Allow any user to register
    
class ListUserView(generics.ListAPIView):
    """_summary_

    Args:
        generics (_type_): _description_
        ListAPIView (_type_): _description_
    """
    queryset =User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]  # Only admin users can list users