import token
from django.forms import ValidationError
from rest_framework import generics, permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from .serializer import (
    EnhancedLocationServiceSerializer, EnhancedUserLocationListSerializer, RegisterUserSerializer, LoginSerializer, CustomerProfileSerializer, 
    CustomerProfileUpdateSerializer, PasswordResetSerializer, 
    PasswordResetConfirmSerializer, PasswordChangeSerializer,
    FlutterRegisterUserSerializer, FlutterLoginSerializer, 
    FlutterCustomerProfileSerializer)
from . import serializer
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from .models import CustomerProfile
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from Users.utils.audit import log_audit_action
from .email import send_registration_email, send_login_notification_email, send_logout_notification_email
import math
from django.db.models import Q

# Enhanced Flutter Registration View
class FlutterRegisterView(generics.CreateAPIView):
    """
    Enhanced registration view optimized for Flutter frontend.
    """
    queryset = User.objects.all()
    serializer_class = FlutterRegisterUserSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        """Handle user registration with Flutter-optimized response."""
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # Log successful registration
            log_audit_action(
                request, 
                details={"email": user.email, "username": user.username}, 
                user=user, 
                action='register', 
                success=True
            )
            
            # Generate tokens for immediate login
            refresh = RefreshToken.for_user(user)
            
            response_data = {
                'success': True,
                'message': 'Registration successful',
                'data': {
                    'user': serializer.to_representation(user),
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token)
                    }
                }
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except serializers.ValidationError as e:
            # Log failed registration
            log_audit_action(
                request=request,
                user=getattr(request, 'user', None),
                action='failed_register',
                details={'reason': e.detail, 'data': request.data},
                success=False
            )
            
            return Response({
                'success': False,
                'message': 'Registration failed',
                'errors': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Registration failed: {str(e)}',
                'errors': {'non_field_errors': [str(e)]}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Enhanced Flutter Login View
class FlutterLoginView(generics.GenericAPIView):
    """
    Enhanced login view optimized for Flutter frontend.
    """
    serializer_class = FlutterLoginSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        """Handle user login with comprehensive response."""
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            user_data = serializer.to_representation(None)
            user = serializer.validated_data['user']
            
            # Update last login
            from django.contrib.auth import update_session_auth_hash
            user.save(update_fields=['last_login'])
            
            # Log successful login
            log_audit_action(
                request, 
                user=user, 
                action='login', 
                details={
                    'ip_address': request.META.get('REMOTE_ADDR'),
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')[:255]
                }, 
                success=True
            )
            
            return Response({
                'success': True,
                'message': 'Login successful',
                'data': user_data
            }, status=status.HTTP_200_OK)
            
        except serializers.ValidationError as e:
            # Log failed login
            log_audit_action(
                request=request,
                user=None,
                action='login_failed',
                details={
                    'reason': e.detail,
                    'attempted_username': request.data.get('username', ''),
                    'ip_address': request.META.get('REMOTE_ADDR')
                },
                success=False
            )
            
            return Response({
                'success': False,
                'message': 'Login failed',
                'errors': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Login failed: {str(e)}',
                'errors': {'non_field_errors': [str(e)]}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Enhanced Flutter Profile View
class FlutterProfileView(generics.RetrieveUpdateAPIView):
    """
    Enhanced profile view optimized for Flutter frontend.
    """
    serializer_class = FlutterCustomerProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """Get or create customer profile for authenticated user."""
        profile, created = CustomerProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'first_name': self.request.user.first_name,
                'last_name': self.request.user.last_name,
                'email': self.request.user.email
            }
        )
        return profile
    
    def retrieve(self, request, *args, **kwargs):
        """Get user profile with Flutter-optimized response."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'success': True,
            'message': 'Profile retrieved successfully',
            'data': serializer.data
        })
    
    def update(self, request, *args, **kwargs):
        """Update user profile with Flutter-optimized response."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            # Log profile update
            log_audit_action(
                request,
                user=request.user,
                action='update_profile',
                details={'updated_fields': list(request.data.keys())},
                success=True
            )
            
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'data': serializer.data
            })
            
        except serializers.ValidationError as e:
            return Response({
                'success': False,
                'message': 'Profile update failed',
                'errors': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)

# Enhanced Flutter Logout View
class FlutterLogoutView(generics.GenericAPIView):
    """
    Enhanced logout view optimized for Flutter frontend.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Handle user logout with token blacklisting."""
        try:
            user = request.user
            
            # Get refresh token from request
            refresh_token = request.data.get('refresh_token')
            
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except TokenError:
                    pass  # Token might already be blacklisted
            
            # Blacklist all user tokens as fallback
            tokens = OutstandingToken.objects.filter(user=user)
            for token in tokens:
                try:
                    BlacklistedToken.objects.get_or_create(token=token)
                except:
                    pass
            
            # Log logout
            log_audit_action(
                request, 
                action='logout', 
                details={'logout_method': 'manual'}, 
                user=user, 
                success=True
            )
            
            return Response({
                'success': True,
                'message': 'Logged out successfully',
                'data': None
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Logout failed: {str(e)}',
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)

# Keep your existing views for backward compatibility
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
    permission_classes = [IsAuthenticated]  # Fix: Require authentication

    def get_object(self):
        return self.request.user
    
    def perform_update(self, serializer):
        # Just save - let DRF handle the response
        serializer.save()

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
   #     log_audit_action(request, 'list_users')
        return super().list(request, *args, **kwargs)

# Additional Flutter-specific endpoints
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def flutter_user_status(request):
    """Get current user status for Flutter app."""
    user = request.user
    
    try:
        profile = user.Customer_profile
    except CustomerProfile.DoesNotExist:
        profile = CustomerProfile.objects.create(
            user=user,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email
        )
    
    return Response({
        'success': True,
        'data': {
            'is_authenticated': True,
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': f"{profile.first_name} {profile.last_name}".strip(),
            'loyalty_points': profile.loyalty_points,
            'account_status': {
                'is_active': user.is_active,
                'last_login': user.last_login.isoformat() if user.last_login else None
            }
        }
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def flutter_check_username(request):
    """Check if username is available."""
    username = request.data.get('username', '').strip()
    
    if not username:
        return Response({
            'success': False,
            'message': 'Username is required',
            'available': False
        }, status=status.HTTP_400_BAD_REQUEST)
    
    is_available = not User.objects.filter(username=username).exists()
    
    return Response({
        'success': True,
        'available': is_available,
        'message': 'Username is available' if is_available else 'Username is already taken'
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def flutter_check_email(request):
    """Check if email is available."""
    email = request.data.get('email', '').strip()
    
    if not email:
        return Response({
            'success': False,
            'message': 'Email is required',
            'available': False
        }, status=status.HTTP_400_BAD_REQUEST)
    
    is_available = not User.objects.filter(email=email).exists()
    
    return Response({
        'success': True,
        'available': is_available,
        'message': 'Email is available' if is_available else 'Email is already registered'
    })

class UserAvailableLocationsView(generics.GenericAPIView):
    """
    Enhanced view for users to see all available locations with complete service information
    """
    permission_classes = [AllowAny]  # Allow any user to view locations
    serializer_class = EnhancedUserLocationListSerializer
    
    def get(self, request, *args, **kwargs):
        """Get all available locations with enhanced filtering and complete service details"""
        try:
            # Create serializer instance
            serializer = self.get_serializer(data={})
            location_data = serializer.to_representation({})
            
            return Response({
                'success': True,
                'message': 'Available locations with services retrieved successfully',
                'data': location_data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Error retrieving locations with services',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Also add a specific endpoint for location services
@api_view(['GET'])
@permission_classes([AllowAny])
def location_services_list(request, location_id=None):
    """Get detailed list of services for a specific location or all locations"""
    try:
        from Location.models import Location, LocationService
        
        if location_id:
            # Get services for specific location
            try:
                location = Location.objects.get(id=location_id)
                services = location.location_services.all().prefetch_related('service')
                
                services_data = EnhancedLocationServiceSerializer(services, many=True).data
                
                return Response({
                    'success': True,
                    'message': f'Services for {location.name} retrieved successfully',
                    'data': {
                        'location': {
                            'id': location.id,
                            'name': location.name,
                            'address': location.address
                        },
                        'services': services_data,
                        'total_services': len(services_data)
                    }
                })
            except Location.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Location not found'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            # Get all location services
            all_services = LocationService.objects.all().select_related('location').prefetch_related('service')
            
            # Group by location
            services_by_location = {}
            for service in all_services:
                location_name = service.location.name
                if location_name not in services_by_location:
                    services_by_location[location_name] = {
                        'location_id': service.location.id,
                        'location_name': location_name,
                        'services': []
                    }
                
                service_data = EnhancedLocationServiceSerializer(service).data
                services_by_location[location_name]['services'].append(service_data)
            
            return Response({
                'success': True,
                'message': 'All location services retrieved successfully',
                'data': {
                    'locations_with_services': list(services_by_location.values()),
                    'total_locations': len(services_by_location),
                    'total_services': all_services.count()
                }
            })
    
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Error retrieving location services',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
