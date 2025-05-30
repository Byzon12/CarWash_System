from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from .serializer import UserSerializer
from django.contrib.auth import get_user_model

# Import necessary modules and classes
# from django.contrib.auth import get_user_model
# Get the user model
User = get_user_model()


class RegisterUserView(generics.CreateAPIView):
    """
    View to register a new user.
    """
    

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]  # Allow any user to register
    
    #function to create a new user but must be a customer
    def perform_create(self, serializer):
        # Ensure the user is created with the role of 'Customer'
        role = self.request.data.get('role', 'Customer')
        if role != 'Customer':
            raise ValueError("Only users with the role 'Customer' can register.")
        serializer.save(role='Customer')
        
        return super().perform_create(serializer)
    
        
    
      # Allow any user to register
    
class ListUserView(generics.ListAPIView):
    """_summary_

    Args:
        generics (_type_): _description_
        ListAPIView (_type_): _description_
    """
    queryset =User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]  # Only admin users can list users