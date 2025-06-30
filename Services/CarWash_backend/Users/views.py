import token
from django.forms import ValidationError
from rest_framework import generics, permissions, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from .serializer import  RegisterUserSerializer, LoginSerializer, CustomerProfileSerializer, CustomerProfileUpdateSerializer,PasswordResetSerializer, PasswordResetConfirmSerializer, PasswordChangeSerializer
from . import serializer
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from .models import CustomerProfile
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken, TokenError  # This import is used to generate JWT tokens for user authentication
from django.contrib.auth.tokens import default_token_generator # This import is used to generate tokens for user authentication
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode # This import is used to decode and encode the user ID from the URL
from django.utils.encoding import force_bytes # This import is used to encode the user ID to bytes for token generation
from django .core.mail import send_mail # This import is used to send emails for user registration and password reset
#importing the log audit function to log user actions
from Users.utils.audit import log_audit_action  # Import the function to log user actions
from .email import send_registration_email, send_login_notification_email, send_logout_notification_email  # Import the function to send registration email


# Import necessary modules and classes
# from django.contrib.auth import get_user_model
# Get the user model





class RegisterUserView(generics.CreateAPIView):
    """
    View to register a new user.
    """
    

    queryset = User.objects.all()
    serializer_class = RegisterUserSerializer
    permission_classes = [AllowAny]  # Allow any user to register


def post(self, request):
    serializer = self.get_serializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        log_audit_action(request, details={"email": user.email}, user=user, action='register', success=True)  # Log the registration action
        # send_registration_email(user)  # Send registration email
        return Response({'message': 'User registered successfully'}, status=201)
    else:
        log_audit_action(
            request=request,
            user=getattr(request, 'user', None),  # fallback if user is not authenticated
            action='failed_register',
            details={'reason': serializer.errors},
            success=False
        )
        return Response(serializer.errors, status=400)
            
         
       
    

#login view
class LoginUserView(generics.GenericAPIView):
    """
    View to handle user login.
    """
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny] # Allow any user to login
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        #logging the login attempt
        
        # Validate the serializer
        
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
    
        # Log the successful login action
        log_audit_action(request, user=user, action='login', details={'ip_address': request.META.get('REMOTE_ADDR')}, success=True)
        # Send a login notification email
        # send_login_notification_email(user, request)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user_id': user.id,
            'username': user.username,
            'email': user.email
        }, status=status.HTTP_200_OK)
        
class LogoutUserView(generics.GenericAPIView):
    """
    View to handle user logout.
    """
    permission_classes = [IsAuthenticated]  # Only authenticated users can logout

    def post(self, request):
        user = request.user # Get the authenticated user from the request
        tokens = OutstandingToken.objects.filter(user=user) # Get all tokens for the user
        
        if not tokens.exists():
            return Response({'error': 'No active session found.'}, status=status.HTTP_400_BAD_REQUEST)
        
        for token in tokens:
            # Blacklist each token to log out the user
            try:
            #if not already blacklisted, blacklist the token
                BlacklistedToken.objects.get_or_create(token=token)
            except TokenError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        log_audit_action(request, action='logout', details='User initiated logout', user=user, success=True)  # Log the logout action

        return Response({'message': 'User logged out successfully.'}, status=status.HTTP_205_RESET_CONTENT)


class CustomerProfileView(generics.RetrieveUpdateAPIView):
    """
    API view for retrieving and updating the authenticated customer's profile.
    - GET: Returns the customer's profile data using `CustomerProfileSerializer`.
    - PUT/PATCH: Updates the customer's profile using `CustomerProfileUpdateSerializer`.
    - Only authenticated users can access this view.
    Methods:
        get_serializer_class: Dynamically selects the serializer based on the HTTP method.
        get_object: Retrieves the `CustomerProfile` instance associated with the authenticated user.
    
    View to retrieve and update the customer profile.
    """
    permission_classes = [IsAuthenticated]  # Only authenticated users can access this view
    
    #dynamic serializer selection based on request method
    def get_serializer_class(self):
        if self.request.method == 'GET':
            # Use CustomerProfileSerializer for GET requests
            # This serializer is used to retrieve the customer's profile data
            
            
            return CustomerProfileSerializer
        elif self.request.method in ['PUT', 'PATCH']:
            return CustomerProfileUpdateSerializer
        return super().get_serializer_class()
    
    def get_object(self):
        # Get the customer profile for the authenticated user
        
        return CustomerProfile.objects.get(user=self.request.user)
    
    
class PasswordResetView(generics.GenericAPIView):
    """
    View to handle password reset requests.
    """
    serializer_class = PasswordResetSerializer
    permission_classes = [permissions.AllowAny]  # Allow any user to request a password reset

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Save the serializer to send the password reset email
        serializer.save()
        
        return Response({'message': 'Password reset email has been sent.'}, status=status.HTTP_200_OK)
        
# view for password reset confirmation
class PasswordResetConfirmView(generics.GenericAPIView):
    """
    View to handle password reset confirmation.
    """
    # Use the same serializer for password reset confirmation
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]
    # Allow any user to confirm password reset
    def post(self, request):
        
        serializers = self.get_serializer(data=request.data)
        serializers.is_valid(raise_exception=True)
        
        serializers.save()
        return Response({'message': 'Password has been reset successfully.'}, status=status.HTTP_200_OK)


class PasswordChangeView(generics.UpdateAPIView):
    """
    View to handle password change for authenticated users.
    """
    serializer_class = serializer.PasswordChangeSerializer
    permission_classes = [AllowAny]  # Only authenticated users can change their password

    def get_object(self):
        # Get the user object for the authenticated user
        return self.request.user

    def perform_update(self, serializer):
        # Save the new password
        serializer.save()
        return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)
   
    
class ListUserView(generics.ListAPIView):
    """_summary_

    Args:
        generics (_type_): _description_
        ListAPIView (_type_): _description_
    """
    queryset =User.objects.all()
    serializer_class = RegisterUserSerializer
    permission_classes = [permissions.AllowAny] # Only admin users can list users
    
    #logging the user listing action
    def list(self, request, *args, **kwargs):
        log_audit_action(request, 'list_users')
        return super().list(request, *args, **kwargs)
    