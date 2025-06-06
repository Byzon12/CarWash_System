from django.forms import ValidationError
from rest_framework import generics, permissions, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from .serializer import  RegisterUserSerializer, LoginSerializer, CustomerProfileSerializer, CustomerProfileUpdateSerializer,PasswordResetSerializer, PasswordResetConfirmSerializer, PasswordChangeSerializer
from . import serializer
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
    
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            log_audit_action(request, 'register')
            return Response({'message': 'User registered successfully.'}, status=status.HTTP_201_CREATED)
        else:
            log_audit_action(request, 'failed_register', {'reason': serializer.errors})
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            
         
       
    

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
        # Generate token or perform any other login logic here
        
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
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            return Response({'error': 'Refresh token is required.'}, status=status.HTTP_400_BAD_REQUEST)
        # Validate the refresh token
        try:
            RefreshToken(refresh_token)  # This will raise an error if the token is invalid
        except TokenError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        # If the token is valid, proceed to logout
        # Log the user out by blacklisting the refresh token
        # This will invalidate the token and prevent further access
        
        try:
            # Blacklist the refresh token to log out the user
            RefreshToken.for_user(request.user).blacklist()
            log_audit_action(request, 'logout')
            return Response({'message': 'User logged out successfully.'}, status=status.HTTP_205_RESET_CONTENT)
        except TokenError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
class CustomerProfileView(generics.RetrieveUpdateAPIView):
    """
    View to retrieve and update the customer profile.
    """
    permission_classes = [IsAuthenticated]  # Only authenticated users can access this view
    
    #dynamic serializer selection based on request method
    def get_serializer_class(self):
        if self.request.method == 'GET':
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
    serializer_class = PasswordResetSerializer  # Use the serializer for password reset
    permission_classes = [permissions.AllowAny]  # Allow any user to request a password reset

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = f"http://127.0.0.1:8000/user/password-reset-confirm/{uid}/{token}/"
            
            send_mail(
                subject='Password Reset Request',
                message= f'Click the link to reset your password: {reset_link}',
               
                from_email= 'byzoneochieng@mail.com',  # from_email (set appropriately)
                recipient_list= [user.email],  # recipient_list
            )
            return Response({'message': 'Password reset email sent.'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'User with this email does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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
    