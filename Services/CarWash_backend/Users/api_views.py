from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import CustomerProfile
from .serializer import (
    RegisterUserSerializer, 
    LoginSerializer, 
    CustomerProfileSerializer,
    CustomerProfileUpdateSerializer
)

class RegisterAPIView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    serializer_class = RegisterUserSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'success': True,
                'message': 'User registered successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class LoginAPIView(generics.GenericAPIView):
    """User login endpoint"""
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            
            user = authenticate(username=username, password=password)
            if user:
                refresh = RefreshToken.for_user(user)
                
                # Get or create customer profile
                profile, created = CustomerProfile.objects.get_or_create(user=user)
                
                return Response({
                    'success': True,
                    'message': 'Login successful',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                    },
                    'profile': {
                        'id': profile.id,
                        'phone_number': profile.phone_number,
                        'address': profile.address,
                        'loyalty_points': profile.loyalty_points,
                    },
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    """Get and update user profile"""
    serializer_class = CustomerProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        profile, created = CustomerProfile.objects.get_or_create(user=self.request.user)
        return profile
    
    def get(self, request, *args, **kwargs):
        profile = self.get_object()
        return Response({
            'success': True,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
            },
            'profile': {
                'id': profile.id,
                'first_name': profile.first_name,
                'last_name': profile.last_name,
                'email': profile.email,
                'phone_number': profile.phone_number,
                'address': profile.address,
                'loyalty_points': profile.loyalty_points,
                'created_at': profile.created_at,
                'updated_at': profile.updated_at,
            }
        })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout user by blacklisting refresh token"""
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({
            'success': True,
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Logout failed'
        }, status=status.HTTP_400_BAD_REQUEST)