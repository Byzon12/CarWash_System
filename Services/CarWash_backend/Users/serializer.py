from django.contrib.auth.models import User
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db.models import Q
from django.contrib.auth.password_validation import validate_password
from .models import CustomerProfile
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
            'password': {'write_only': False, 'min_length': 8},
            'confirm_password': {'write_only': False, 'min_length': 8}
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
      
      
      
      
      #updating userprofile
class CustomerProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source ="user.first_name")
    last_name = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(max_length=255, source='user.email')

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
    fields = ['first_name', 'last_name', 'email', 'phone_number', 'address', 'loyalty_points']
    extra_kwargs = {
        'phone_number': {'required': False, 'allow_blank': True},
        'address': {'required': False, 'allow_blank': True},
        'loyalty_points': {'read_only': True}
    }
    
class CustomerProfileUpdateSerializer(serializers.ModelSerializer):
    """
    serializer for updating customer profile information.
    
        """
username = serializers.CharField(
    source='user.username',
    max_length=150,
    validators=[UnicodeUsernameValidator()],
    error_messages={
        'blank': _('Username cannot be blank.'),
        'max_length': _('Username cannot exceed 150 characters.')
    }
)
email = serializers.EmailField(
    source='user.email',
    required=False,
    error_messages={
        'blank': _('Email cannot be blank.'),
        'invalid': _('Enter a valid email address.')
    }
)
first_name = serializers.CharField(
    source='user.first_name',
    max_length=255,
    error_messages={
        'blank': _('First name cannot be blank.'),
        'max_length': _('First name cannot exceed 255 characters.')
    }
)
last_name = serializers.CharField(
    source='user.last_name',
    max_length=255,
    error_messages={
        'blank': _('Last name cannot be blank.'),
        'max_length': _('Last name cannot exceed 255 characters.')
    }
)
phone_number = serializers.CharField(
    max_length=15,
    required=False,
    allow_blank=True,
    error_messages={
        'max_length': _('Phone number cannot exceed 15 characters.')
    }
)
address = serializers.CharField(
    allow_blank=True,
    required=False,
    error_messages={
        'blank': _('Address cannot be blank.')
    }
)
loyalty_points = serializers.IntegerField(
    read_only=True,
    error_messages={
        'read_only': _('Loyalty points cannot be modified directly.')
    }
)
class Meta:
    model = CustomerProfile
    fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'address', 'loyalty_points']
    extra_kwargs = {
        'username': {'required': True, 'allow_blank': False},
        'email': {'required': False},
        'first_name': {'required': True},
        'last_name': {'required': True},
        'phone_number': {'required': False, 'allow_blank': True},
        'address': {'required': False, 'allow_blank': True}
    }
def update(self, instance, validated_data):
    user_data = validated_data.pop('user', {})
    for attr, value in user_data.items():
        setattr(instance.user, attr, value)
    instance.user.save()
    for attr, value in validated_data.items():
        setattr(instance, attr, value)
    instance.save()
    return instance