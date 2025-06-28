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

from .email import send_password_reset_email
#from Services.CarWash_backend.Users.authentication import UsernameOrEmailBackend
from .models import CustomerProfile
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
def validate_email(value):
    raise NotImplementedError

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
