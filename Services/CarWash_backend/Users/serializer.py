from importlib.util import source_from_cache
from os import read
from turtle import reset
from typing import Required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db.models import Q
from django.contrib.auth.password_validation import validate_password
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from rest_framework_simplejwt.tokens import RefreshToken

from .email import send_password_reset_email
from .models import CustomerProfile
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Sum, Count, Avg, Q
from decimal import Decimal
import math

def validate_email(value):
    raise NotImplementedError

# Enhanced Registration Serializer for Flutter
class FlutterRegisterUserSerializer(serializers.ModelSerializer):
    """
    Enhanced serializer for user registration optimized for Flutter frontend.
    """
    username = serializers.CharField(
        max_length=150,
        validators=[UnicodeUsernameValidator()],
        error_messages={
            'blank': _('Username cannot be blank.'),
            'max_length': _('Username cannot exceed 150 characters.'),
            'required': _('Username is required.')
        }
    )
    
    email = serializers.EmailField(
        error_messages={
            'blank': _('Email cannot be blank.'),
            'invalid': _('Enter a valid email address.'),
            'required': _('Email is required.')
        }
    )
    
    first_name = serializers.CharField(
        max_length=255,
        error_messages={
            'blank': _('First name cannot be blank.'),
            'max_length': _('First name cannot exceed 255 characters.'),
            'required': _('First name is required.')
        }
    )
    
    last_name = serializers.CharField(
        max_length=255,
        error_messages={
            'blank': _('Last name cannot be blank.'),
            'max_length': _('Last name cannot exceed 255 characters.'),
            'required': _('Last name is required.')
        }
    )
    
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        error_messages={
            'blank': _('Password cannot be blank.'),
            'min_length': _('Password must be at least 8 characters long.'),
            'required': _('Password is required.')
        }
    )
    
    confirm_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        error_messages={
            'blank': _('Confirm password cannot be blank.'),
            'required': _('Confirm password is required.')
        }
    )
    
    # Optional fields for enhanced profile
    phone_number = serializers.CharField(
        max_length=15, 
        required=False, 
        allow_blank=True,
        error_messages={
            'max_length': _('Phone number cannot exceed 15 characters.')
        }
    )
    
    address = serializers.CharField(
        required=False, 
        allow_blank=True,
        error_messages={
            'max_length': _('Address cannot exceed 500 characters.')
        }
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 
            'password', 'confirm_password', 'phone_number', 'address'
        ]
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 8},
            'confirm_password': {'write_only': True}
        }
    
    def validate_username(self, value):
        """Validate the uniqueness of the username field."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(_('Username already exists.'))
        return value
    
    def validate_email(self, value):
        """Validate the uniqueness of the email field."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(_('Email already exists.'))
        return value
    
    def validate_phone_number(self, value):
        """Validate phone number format."""
        if value and not value.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise serializers.ValidationError(_('Enter a valid phone number.'))
        return value
    
    def validate(self, attrs):
        """Validate password confirmation and strength."""
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'password': _('Passwords do not match.'),
                'confirm_password': _('Passwords do not match.')
            })
        
        try:
            validate_password(attrs['password'])
        except ValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        
        return attrs
    
    def create(self, validated_data):
        """Create a new user instance with CustomerProfile."""
        # Extract profile data
        phone_number = validated_data.pop('phone_number', '')
        address = validated_data.pop('address', '')
        validated_data.pop('confirm_password', None)
        
        # Create user
        user = User.objects.create_user(**validated_data)
        
        # Create or update customer profile
        customer_profile, created = CustomerProfile.objects.get_or_create(
            user=user,
            defaults={
                'first_name': validated_data.get('first_name', ''),
                'last_name': validated_data.get('last_name', ''),
                'email': validated_data.get('email', ''),
                'phone_number': phone_number,
                'address': address,
                'loyalty_points': 0
            }
        )
        
        return user
    
    def to_representation(self, instance):
        """Return Flutter-friendly response format."""
        try:
            profile = instance.Customer_profile
        except CustomerProfile.DoesNotExist:
            profile = None
        
        return {
            'user_id': instance.id,
            'username': instance.username,
            'email': instance.email,
            'first_name': instance.first_name,
            'last_name': instance.last_name,
            'profile': {
                'phone_number': profile.phone_number if profile else '',
                'address': profile.address if profile else '',
                'loyalty_points': profile.loyalty_points if profile else 0,
                'created_at': profile.created_at.isoformat() if profile and profile.created_at else None
            },
            'date_joined': instance.date_joined.isoformat(),
            'is_active': instance.is_active
        }

# Enhanced Login Serializer for Flutter
class FlutterLoginSerializer(serializers.Serializer):
    """
    Enhanced login serializer optimized for Flutter frontend.
    """
    username = serializers.CharField(
        error_messages={
            'blank': _('Username or email cannot be blank.'),
            'required': _('Username or email is required.')
        }
    )
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        error_messages={
            'blank': _('Password cannot be blank.'),
            'required': _('Password is required.')
        }
    )
    remember_me = serializers.BooleanField(default=False, required=False)
    
    def validate(self, attrs):
        """Validate login credentials."""
        username = attrs.get('username', '').strip()
        password = attrs.get('password')
        
        if not username or not password:
            raise serializers.ValidationError(_('Both username/email and password are required.'))
        
        try:
            # Try to find user by username or email
            user = User.objects.get(Q(username=username) | Q(email=username))
        except User.DoesNotExist:
            raise serializers.ValidationError(_('Invalid credentials. Please check your username/email and password.'))
        
        if not user.is_active:
            raise serializers.ValidationError(_('Account is deactivated. Please contact support.'))
        
        if not user.check_password(password):
            raise serializers.ValidationError(_('Invalid credentials. Please check your username/email and password.'))
        
        attrs['user'] = user
        return attrs
    
    def get_tokens_for_user(self, user):
        """Generate JWT tokens for user."""
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    
    def to_representation(self, instance):
        """Return complete user data with tokens for Flutter."""
        user = self.validated_data['user']
        tokens = self.get_tokens_for_user(user)
        
        try:
            profile = user.Customer_profile
        except CustomerProfile.DoesNotExist:
            # Create profile if it doesn't exist
            profile = CustomerProfile.objects.create(
                user=user,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email
            )
        
        return {
            'tokens': tokens,
            'user': {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'profile': {
                    'phone_number': profile.phone_number or '',
                    'address': profile.address or '',
                    'loyalty_points': profile.loyalty_points,
                    'created_at': profile.created_at.isoformat() if profile.created_at else None,
                    'updated_at': profile.updated_at.isoformat() if profile.updated_at else None
                },
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'is_active': user.is_active
            }
        }

# Enhanced Customer Profile Serializer for Flutter
class FlutterCustomerProfileSerializer(serializers.ModelSerializer):
    """
    Enhanced customer profile serializer for Flutter frontend.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email')
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    full_name = serializers.SerializerMethodField()
    initials = serializers.SerializerMethodField()
    account_status = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomerProfile
        fields = [
            'user_id', 'username', 'email', 'first_name', 'last_name', 
            'full_name', 'initials', 'phone_number', 'address', 
            'loyalty_points', 'account_status', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'phone_number': {'required': False, 'allow_blank': True},
            'address': {'required': False, 'allow_blank': True},
            'loyalty_points': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True}
        }
    
    def get_full_name(self, obj):
        """Get user's full name."""
        return f"{obj.first_name} {obj.last_name}".strip() or obj.user.username
    
    def get_initials(self, obj):
        """Get user's initials."""
        first_initial = obj.first_name[0].upper() if obj.first_name else ''
        last_initial = obj.last_name[0].upper() if obj.last_name else ''
        return f"{first_initial}{last_initial}" or obj.user.username[0].upper()
    
    def get_account_status(self, obj):
        """Get account status information."""
        return {
            'is_active': obj.user.is_active,
            'last_login': obj.user.last_login.isoformat() if obj.user.last_login else None,
            'date_joined': obj.user.date_joined.isoformat()
        }
    
    def validate_email(self, value):
        """Validate email uniqueness."""
        user = self.instance.user if self.instance else None
        if User.objects.filter(email=value).exclude(pk=user.pk if user else None).exists():
            raise serializers.ValidationError(_('Email already exists.'))
        return value
    
    def validate_phone_number(self, value):
        """Validate phone number format."""
        if value and not value.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise serializers.ValidationError(_('Enter a valid phone number.'))
        return value
    
    def update(self, instance, validated_data):
        """Update profile and related user data."""
        user_data = validated_data.pop('user', {})
        
        # Update user fields
        if 'email' in user_data:
            instance.user.email = user_data['email']
            instance.email = user_data['email']  # Keep profile email in sync
            instance.user.save()
        
        # Update profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

# Keep your existing serializers but add these new ones
class RegisterUserSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """
    username = serializers.CharField(
        max_length=150,
        validators=[UnicodeUsernameValidator()],
        error_messages={
            'blank': _('Username cannot be blank.'),
            'max_length': _('Username cannot exceed 150 characters.')
        }
    )
    
    email = serializers.EmailField(
        error_messages={
            'blank': _('Email cannot be blank.'),
            'invalid': _('Enter a valid email address.')
        }
    )
    
    first_name = serializers.CharField(
        max_length=255,
        error_messages={
            'blank': _('Full name cannot be blank.'),
            'max_length': _('Firts name cannot exceed 255 characters.')
        }
    )
    
    last_name = serializers.CharField(
        max_length=255,
        error_messages={
            'blank': _('Last name cannot be blank.'),
            'max_length': _('Last name cannot exceed 255 characters.')
        }
    )
    
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        error_messages={
            'blank': _('Password cannot be blank.'),
            'max_length': _('Password cannot exceed 255 characters.'),
            'min_length': _('Password must be at least 8 characters long.')
        }
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        error_messages={
            'blank': _('Confirm password cannot be blank.'),
            'max_length': _('Confirm password cannot exceed 255 characters.')
        }
    )
    
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name','last_name', 'password', 'confirm_password']
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 8},
            'confirm_password': {'write_only': True, 'min_length': 8}
        }
        
        #method to validate the uniqueness of the username field
    def validate_username(self, value):
        """        Validate the uniqueness of the username field.
        
        """
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(_('Username already exists.'))
        return value
    
    #function for email validation
    
    
    def validate_email(self, value):
        """
      validate the uniquenness of the email field.
        
        """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(_('Email already exists.'))
        return value
    
    def validate(self, attrs):
        """
        Validate the password and confirm_password fields.
        Ensure that they match and meet the required criteria.
        
        """
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError(_('Passwords do not match.'))
        
        try:
            validate_password(attrs['password'])
        except ValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        

        return attrs
    
    def create(self, validated_data):
        """
        Create a new user instance.
        """
        validated_data.pop('confirm_password', None)  # Remove confirm_password from validated_data
        user = User.objects.create_user(**validated_data)
       # user.set_password(validated_data['password'])
        user.save()
        return user
    
 #LOGING SERIALIZER CLASS.   
 
class LoginSerializer(serializers.Serializer):
      username = serializers.CharField() #can be username or email
      password = serializers.CharField(write_only=True, style={'input_type': 'password'})
      
      def validate(self, attrs):
          username = attrs.get('username')
          password = attrs.get('password')
          if username and password:
              try:
                  user = User.objects.get(Q(username=username) | Q(email=username))
              except User.DoesNotExist:
                  raise serializers.ValidationError(_('Invalid username or password.'))
              
              if not user.check_password(password):
                  raise serializers.ValidationError(_('Invalid username or password.'))
              
              attrs['user'] = user
          return attrs
      
      
      
      
      
  #class serializer for password rquests reset
class PasswordResetSerializer(serializers.Serializer):
    """Serializer for handling password reset requests.
    This serializer validates the email address provided for password reset.
    """
    email = serializers.EmailField(
        max_length=255,
        error_messages={
            'blank': _('Email cannot be blank.'),
            'invalid': _('Enter a valid email address.')
        }
    )
    
   
    def validate_email(self, value):
        """
        Validate the email address for password reset.
        Ensure that the email exists in the system.
        """

        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError(_('Email does not exist.'))
        return value

        #overriding save method to send password reset email
    def save(self, **kwargs):
        request = self.context.get('request')
        email = self.validated_data['email']
        user = User.objects.filter(email=email).first()
        if not user:
            raise serializers.ValidationError(_('User with this email does not exist.'))

        # Generate password reset token
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        # Send password reset email
        send_password_reset_email(user, token, uid, request)

class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming password reset.
    This serializer validates the new password and ensures it meets the required criteria.
    
    """
    uid = serializers.CharField(
        write_only=True,
        error_messages={
            'blank': _('User ID cannot be blank.'),
            'max_length': _('User ID cannot exceed 255 characters.')
        }
    )
    tokens = serializers.CharField(
        write_only=True,
        error_messages={
            'blank': _('Token cannot be blank.'),
            'max_length': _('Token cannot exceed 255 characters.')
        }
     
    )
    new_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        error_messages={
            'blank': _('New password cannot be blank.'),
            'max_length': _('New password cannot exceed 255 characters.'),
            'min_length': _('New password must be at least 8 characters long.')
        }
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        error_messages={
            'blank': _('Confirm password cannot be blank.'),
            'max_length': _('Confirm password cannot exceed 255 characters.')
        }
    )
    
         
    def validate(self, attrs):
        """
        Validate the new password and confirm_password fields.
        Ensure that they match and meet the required criteria.
        """
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError(_('Passwords do not match.'))
        
        try:
            validate_password(attrs['new_password'])
        except ValidationError as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})
        
        # Validate the uid and token
        try:
            uid = urlsafe_base64_decode(attrs['uid']).decode('utf-8')
            user = User.objects.get(pk=uid)
            self.user = user

        except (ValueError, User.DoesNotExist):
            raise serializers.ValidationError(_('Invalid user ID.'))
        
        if not default_token_generator.check_token(user, attrs['tokens']):
            raise serializers.ValidationError(_('Invalid token.'))
        
        #store the user in validated_data for later use
        self.user = user
        return attrs

    def save(self, **kwargs):
        """
        Save the new password for the user.
        """
        password = self.validated_data['new_password']
        user= self.user
        user.set_password(password)  # Set the new password
        
        self.user.save()
        return self.user

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        error_messages={
            'blank': _('Old password cannot be blank.'),
            'max_length': _('Old password cannot exceed 255 characters.'),
            'min_length': _('Old password must be at least 8 characters long.')
        }
    )
    new_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        error_messages={
            'blank': _('New password cannot be blank.'),
            'max_length': _('New password cannot exceed 255 characters.'),
            'min_length': _('New password must be at least 8 characters long.')
        }
    )
    confirm_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        error_messages={
            'blank': _('Confirm password cannot be blank.'),
            'max_length': _('Confirm password cannot exceed 255 characters.')
        }
    )
    def validate_new_password(self, value):
        """
        checks the new password and confirm_password fields.
        Ensure that they match and meet the required criteria.
        Validate the new password.
        Ensure that it meets the required criteria.
        """
        confirm_password = self.initial_data.get('confirm_password')
        if value != confirm_password:
            raise serializers.ValidationError(_('Passwords do not match.'))
        
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})
        return value
    
    def validate(self, attrs):
        """
        Validate the old password.
        Ensure that it matches the user's current password.
        """
        user = self.context['request'].user
        old_password = attrs.get('old_password')
        if not user.check_password(old_password):
            raise serializers.ValidationError(_('Old password is incorrect.'))
        
        return attrs
    
    
    def save(self, **kwargs):
        """
        Save the new password for the user.
        This method is called after validation to update the user's password.
        """
        user = self.context['request'].user
        new_password = self.validated_data['new_password']
        user.set_password(new_password)
        user.save()
        return user

#updating userprofile
class CustomerProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(max_length=255, source='user.email')
    username = serializers.CharField(
        source='user.username',
        read_only=True
    )

    class Meta:
        """
        Meta class for the serializer, specifying the model and fields to be serialized.
        Attributes:
            model (User): The User model associated with this serializer.
            fields (list): List of fields to include in the serialization.
            extra_kwargs (dict): Additional keyword arguments for field-level options, such as making certain fields optional or read-only.
        Methods:
            update(instance, validated_data):
                Updates the instance with validated data, handling nested user data if present.
                Args:
                    instance: The model instance to update.
                    validated_data (dict): The validated data to update the instance with.
                Returns:
                    The updated instance.
        """
        model = CustomerProfile
        fields = ['username','first_name', 'last_name', 'email', 'phone_number', 'address', 'loyalty_points']
        extra_kwargs = {
            'phone_number': {'required': False, 'allow_blank': True},
            'address': {'required': False, 'allow_blank': True},
            'loyalty_points': {'read_only': True}
        }

    def validate_email(self, value):
        """
        Validate the email address for password reset.
        Ensure that the email exists in the system.
        """
        if not CustomerProfile.objects.filter(email=value).exists():
            raise serializers.ValidationError(_('Email does not exist.'))
        return value
        # this serializer get email of the requested password related user and. and handle the reset logic to enable password reset

  
    
    
    #class CustomerProfileUpdateSerializer(serializers.ModelSerializer):
class CustomerProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating the customer profile.
    This serializer allows updating the user's first name, last name, email, phone number, and address.
    """
    username = serializers.CharField(
        source='user.username',
        read_only=True,
    )
    
    class Meta:
        model = CustomerProfile
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'address']
        extra_kwargs = {
            'phone_number': {'required': False, 'allow_blank': True},
            'address': {'required': False, 'allow_blank': True}
        }
    def validate_email(self, value):
        """
        Validate the email address for updating the customer profile.
        Ensure that the email does not already exist for another user.
        
        """
        if CustomerProfile.objects.filter(email=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError(_('Email already exists.'))
        return value
    def update(self, instance, validated_data):
        """ updates the customer profile instance with the validated data."""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class ServiceDetailSerializer(serializers.Serializer):
    """Detailed serializer for individual services"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    price = serializers.SerializerMethodField()
    description = serializers.CharField()
    
    def get_price(self, obj):
        """Get service price as string"""
        try:
            return str(obj.price) if obj.price else "0.00"
        except:
            return "0.00"

class EnhancedLocationServiceSerializer(serializers.Serializer):
    """Enhanced serializer for location services with complete details"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    duration = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    services_included = serializers.SerializerMethodField()
    service_count = serializers.SerializerMethodField()
    is_popular = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    booking_count = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    
    def get_duration(self, obj):
        """Format duration in readable format"""
        try:
            if obj.duration:
                total_seconds = int(obj.duration.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                
                if hours > 0:
                    return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
                else:
                    return f"{minutes}m"
            return "N/A"
        except:
            return "N/A"
    
    def get_total_price(self, obj):
        """Calculate total price of all services in package"""
        try:
            total = sum(service.price or 0 for service in obj.service.all())
            return str(total)
        except:
            return "0.00"
    
    def get_services_included(self, obj):
        """Get detailed list of services in this package"""
        try:
            return ServiceDetailSerializer(obj.service.all(), many=True).data
        except:
            return []
    
    def get_service_count(self, obj):
        """Get count of services in this package"""
        try:
            return obj.service.count()
        except:
            return 0
    
    def get_is_popular(self, obj):
        """Check if this is a popular service based on bookings"""
        try:
            from booking.models import booking
            booking_count = booking.objects.filter(location_service=obj).count()
            return booking_count >= 10  # Adjust threshold as needed
        except:
            return False
    
    def get_average_rating(self, obj):
        """Get average rating for this service package"""
        try:
            from booking.models import booking
            from django.db.models import Avg
            
            ratings = booking.objects.filter(
                location_service=obj,
                rating__isnull=False
            ).aggregate(avg_rating=Avg('rating'))
            
            return round(ratings['avg_rating'], 1) if ratings['avg_rating'] else 0.0
        except:
            return 0.0
    
    def get_booking_count(self, obj):
        """Get total bookings for this service package"""
        try:
            from booking.models import booking
            return booking.objects.filter(location_service=obj).count()
        except:
            return 0

class EnhancedAvailableLocationSerializer(serializers.Serializer):
    """Enhanced serializer for locations with comprehensive location services"""
    # Basic location information
    id = serializers.IntegerField()
    name = serializers.CharField()
    address = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    contact_number = serializers.CharField()
    email = serializers.EmailField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    
    # Enhanced location services information
    location_services = serializers.SerializerMethodField()
    total_services = serializers.SerializerMethodField()
    price_range = serializers.SerializerMethodField()
    popular_services = serializers.SerializerMethodField()
    
    # Location statistics
    distance = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    total_bookings = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    is_open = serializers.SerializerMethodField()
    
    # Business information
    business_info = serializers.SerializerMethodField()
    features = serializers.SerializerMethodField()
    
    def get_location_services(self, obj):
        """Get all location services (packages) with complete details"""
        try:
            services = obj.location_services.all().prefetch_related('service')
            return EnhancedLocationServiceSerializer(services, many=True).data
        except:
            return []
    
    def get_total_services(self, obj):
        """Get total number of service packages"""
        try:
            return obj.location_services.count()
        except:
            return 0
    
    def get_price_range(self, obj):
        """Get price range for services at this location"""
        try:
            services = obj.location_services.all()
            if not services:
                return {"min": "0.00", "max": "0.00"}
            
            prices = []
            for service in services:
                total_price = sum(s.price or 0 for s in service.service.all())
                prices.append(total_price)
            
            if prices:
                return {
                    "min": str(min(prices)),
                    "max": str(max(prices)),
                    "currency": "KES"  # Adjust currency as needed
                }
            return {"min": "0.00", "max": "0.00"}
        except:
            return {"min": "0.00", "max": "0.00"}
    
    def get_popular_services(self, obj):
        """Get top 3 most popular services at this location"""
        try:
            from booking.models import booking
            from django.db.models import Count
            
            popular = obj.location_services.annotate(
                booking_count=Count('booking')
            ).filter(
                booking_count__gt=0
            ).order_by('-booking_count')[:3]
            
            return [
                {
                    'id': service.id,
                    'name': service.name,
                    'booking_count': service.booking_count,
                    'price': str(sum(s.price or 0 for s in service.service.all()))
                }
                for service in popular
            ]
        except:
            return []
    
    def get_distance(self, obj):
        """Calculate distance from user location"""
        request = self.context.get('request')
        if request and request.query_params.get('user_lat') and request.query_params.get('user_lng'):
            try:
                import math
                user_lat = float(request.query_params.get('user_lat'))
                user_lng = float(request.query_params.get('user_lng'))
                
                # Haversine formula for accurate distance calculation
                lat_diff = math.radians(obj.latitude - user_lat)
                lng_diff = math.radians(obj.longitude - user_lng)
                
                a = (math.sin(lat_diff / 2) ** 2 + 
                     math.cos(math.radians(user_lat)) * math.cos(math.radians(obj.latitude)) * 
                     math.sin(lng_diff / 2) ** 2)
                c = 2 * math.asin(math.sqrt(a))
                distance = 6371 * c  # Earth's radius in kilometers
                
                return round(distance, 2)
            except (ValueError, TypeError):
                pass
        return None
    
    def get_average_rating(self, obj):
        """Get average rating for this location"""
        try:
            from booking.models import booking
            from django.db.models import Avg
            
            ratings = booking.objects.filter(
                location=obj,
                rating__isnull=False
            ).aggregate(avg_rating=Avg('rating'))
            
            return round(ratings['avg_rating'], 1) if ratings['avg_rating'] else 0.0
        except:
            return 0.0
    
    def get_total_bookings(self, obj):
        """Get total bookings for this location"""
        try:
            from booking.models import booking
            return booking.objects.filter(location=obj).count()
        except:
            return 0
    
    def get_completion_rate(self, obj):
        """Calculate booking completion rate"""
        try:
            from booking.models import booking
            total = booking.objects.filter(location=obj).count()
            completed = booking.objects.filter(location=obj, status='completed').count()
            return round((completed / total * 100) if total > 0 else 0, 2)
        except:
            return 0.0
    
    def get_is_open(self, obj):
        """Check if location is currently open"""
        # For now, assume all locations are open
        # You can implement actual business hours logic here
        from datetime import datetime
        current_hour = datetime.now().hour
        return 8 <= current_hour <= 18  # Open from 8 AM to 6 PM
    
    def get_business_info(self, obj):
        """Get comprehensive business information"""
        return {
            'contact_number': obj.contact_number or '',
            'email': obj.email or '',
            'operating_hours': {
                'monday': '8:00 AM - 6:00 PM',
                'tuesday': '8:00 AM - 6:00 PM',
                'wednesday': '8:00 AM - 6:00 PM',
                'thursday': '8:00 AM - 6:00 PM',
                'friday': '8:00 AM - 6:00 PM',
                'saturday': '9:00 AM - 5:00 PM',
                'sunday': '10:00 AM - 4:00 PM'
            },
            'payment_methods': ['Cash', 'M-Pesa', 'Credit Card', 'Visa'],
            'languages': ['English', 'Swahili'],
            'parking': 'Available',
            'accessibility': 'Wheelchair accessible'
        }
    
    def get_features(self, obj):
        """Get location features and amenities"""
        return [
            'Free WiFi',
            'Comfortable Waiting Area',
            'Restrooms',
            'Coffee/Tea Service',
            'Air Conditioning',
            'CCTV Security',
            'Covered Parking',
            'Mobile Payment'
        ]

class EnhancedUserLocationListSerializer(serializers.Serializer):
    """Enhanced main serializer for listing locations with complete services"""
    
    def to_representation(self, instance):
        """Custom representation with enhanced location services"""
        request = self.context.get('request')
        
        try:
            from Location.models import Location
        except ImportError:
            return {
                'success': False,
                'message': 'Location module not available',
                'data': {
                    'locations': [],
                    'total_locations': 0,
                    'statistics': {}
                }
            }
        
        # Get all locations with prefetched relationships for better performance
        locations_queryset = Location.objects.select_related('tenant').prefetch_related(
            'location_services',
            'location_services__service'
        ).order_by('name')
        
        # Apply search filter
        search = request.query_params.get('search') if request else None
        if search:
            from django.db.models import Q
            locations_queryset = locations_queryset.filter(
                Q(name__icontains=search) | 
                Q(address__icontains=search) |
                Q(location_services__name__icontains=search) |
                Q(location_services__service__name__icontains=search)
            ).distinct()
        
        # Apply filters
        min_rating = request.query_params.get('min_rating') if request else None
        max_distance = request.query_params.get('max_distance') if request else None
        service_type = request.query_params.get('service_type') if request else None
        
        # Filter by service type
        if service_type:
            locations_queryset = locations_queryset.filter(
                location_services__service__name__icontains=service_type
            ).distinct()
        
        filtered_locations = []
        total_services = 0
        total_bookings = 0
        total_revenue = 0
        
        for location in locations_queryset:
            location_data = EnhancedAvailableLocationSerializer(
                location, 
                context={'request': request}
            ).data
            
            # Apply rating filter
            if min_rating:
                try:
                    if float(location_data['average_rating']) < float(min_rating):
                        continue
                except (ValueError, TypeError):
                    continue
            
            # Apply distance filter
            if max_distance and location_data['distance']:
                try:
                    if float(location_data['distance']) > float(max_distance):
                        continue
                except (ValueError, TypeError):
                    pass
            
            filtered_locations.append(location_data)
            
            # Calculate statistics
            total_services += location_data['total_services']
            total_bookings += location_data['total_bookings']
            
            # Calculate total revenue
            try:
                from booking.models import booking
                from django.db.models import Sum
                location_revenue = booking.objects.filter(
                    location=location,
                    status='completed',
                    payment_status='paid'
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                total_revenue += float(location_revenue)
            except:
                pass
        
        # Sort by distance if user location provided
        user_lat = request.query_params.get('user_lat') if request else None
        user_lng = request.query_params.get('user_lng') if request else None
        
        if user_lat and user_lng:
            filtered_locations.sort(
                key=lambda x: x['distance'] if x['distance'] is not None else float('inf')
            )
        
        return {
            'total_locations': len(filtered_locations),
            'locations': filtered_locations,
            'statistics': {
                'total_services': total_services,
                'total_bookings': total_bookings,
                'total_revenue': str(total_revenue),
                'average_rating': round(
                    sum(loc['average_rating'] for loc in filtered_locations) / len(filtered_locations)
                    if filtered_locations else 0, 1
                ),
                'locations_with_services': sum(
                    1 for loc in filtered_locations if loc['total_services'] > 0
                )
            },
            'search_criteria': {
                'search_term': search,
                'min_rating': min_rating,
                'max_distance': max_distance,
                'service_type': service_type,
                'user_location': {
                    'latitude': user_lat,
                    'longitude': user_lng
                } if user_lat and user_lng else None
            }
        }
