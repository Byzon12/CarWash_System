from django.forms import ValidationError
from rest_framework import generics, permissions, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from .serializer import  RegisterUserSerializer, LoginSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

# Import necessary modules and classes
# from django.contrib.auth import get_user_model
# Get the user model





class RegisterUserView(generics.CreateAPIView):
    """
    View to register a new user.
    """
    

    queryset = User.objects.all()
    serializer_class = RegisterUserSerializer
    permission_classes = [permissions.AllowAny]  # Allow any user to register
    

#login view
class LoginUserView(generics.GenericAPIView):
    """
    View to handle user login.
    """
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny] # Allow any user to login
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        # Generate token or perform any other login logic here
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user_id': user.id,
            'username': user.username,
            'email': user.email
        }, status=status.HTTP_200_OK)
    
    
class ListUserView(generics.ListAPIView):
    """_summary_

    Args:
        generics (_type_): _description_
        ListAPIView (_type_): _description_
    """
    queryset =User.objects.all()
    serializer_class = RegisterUserSerializer
    permission_classes = [permissions.AllowAny]  # Only admin users can list users