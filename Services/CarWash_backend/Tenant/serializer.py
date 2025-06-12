
from ctypes import FormatError
from email import message
from os import read
from urllib import request
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db.models import Q
from Tenant.models import Employee, TenantProfile, Tenant, EmployeeRole
from django.contrib.auth.hashers import check_password

# serializer to handle Tenant login with the username and password
class TenantLoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=150,
        min_length=3,
        validators=[UnicodeUsernameValidator()],
        error_messages={
            'blank': _('Username cannot be blank.'),
            'max_length': _('Username cannot exceed 150 characters.'),
            'min_length': _('Username must be at least 3 characters long.')
        }
    )
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        error_messages={
            'blank': _('Password cannot be blank.')
        }
    )

    def validate(self, data):
        """Validate the username and password."""
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            raise serializers.ValidationError(_('Username and password are required.'))
        
        try:
            tenant_profile = TenantProfile.objects.get(
                Q(business_email=username) | Q(username=username)
            )
           
        except TenantProfile.DoesNotExist:
            raise serializers.ValidationError(_('Invalid username or password.'))

        tenant = tenant_profile.tenant
        if not check_password(password, tenant.password):
            raise serializers.ValidationError(_('Invalid username or password.'))
        data['tenant'] = tenant
        data['tenant_profile'] = tenant_profile

        return data
    # method to return the tenant profile
    def get_tenant_profile(self):
        """Return the tenant profile associated with the validated data."""
        tenant = self.validated_data.get('tenant', None)
        if tenant:
          """  return {
                'tenant_profile': {
                    'id': self.validated_data['tenant_profile'].pk,
                    'business_name': self.validated_data['tenant_profile'].business_name,
                    'business_email': self.validated_data['tenant_profile'].business_email,
                    'phone_number': self.validated_data['tenant_profile'].phone_number,
                        'address': self.validated_data['tenant_profile'].address,
                        'created_at': self.validated_data['tenant_profile'].created_at,
                        'updated_at': self.validated_data['tenant_profile'].updated_at
                    }
                }"""
        return f"Tenant Profile for {tenant.name} with ID {tenant.id}"

    
    def get_tenant(self):
       return self.validated_data.get('tenant', None)

    # method to return the tenant profile
# TenantProfile Serializer
class TenantProfileSerializer(serializers.ModelSerializer):
    tenant = serializers.StringRelatedField(read_only=True)
    name = serializers.CharField(source='tenant.name', read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = TenantProfile
        fields = '__all__'
     
    # method to validate bussiness email, bussiness_name and phone number

    def validate(self, data):
        """custom validation to ensure business email, business name and phone number are valid and unique."""
        phone_number = data.get('phone_number')
        # validate bussiness email if it ends with @tenant.com
        business_email = data.get('bussiness_email')
        if business_email and not business_email.endswith('@tenant.com'):
            raise serializers.ValidationError({
                'bussiness_email': _('Business email must be a valid tenant email.')
            })
        # validate phone number if it is not empty and does not start with +254
        if phone_number and not phone_number.startswith('+254'):
            raise serializers.ValidationError({
                'phone_number':( _('Phone number must be in international format. must start with +254.'))
            })
      
        return data

    # validate if the business name is already taken
    def validate_business_name(self, value):
        if TenantProfile.objects.filter(business_name__iexact=value).exists():
            raise serializers.ValidationError(_('Business name already exists.'))
        return value

# perform update method to ensure that the tenant profile is updated correctly
    def update(self, instance, validated_data):# -> Any:
        """Update the tenant profile instance with validated data."""
        # Update the tenant profile instance with the validated data
        validated_data['tenant'] = self.context.get('request').tenant if hasattr(self.context.get('request'), 'tenant') else None
        return super().update(instance, validated_data)

    def create(self, validated_data):
        """Create a new tenant profile instance."""
        request = self.context.get('request')
        tenant = request.tenant if hasattr(request, 'tenant') else None
        if not tenant:
            raise ValidationError(_('Tenant must be set.'))
        validated_data['tenant'] = tenant
        return super().create(validated_data)



# serializer to handle employee role and salary
class EmployeeRoleSalarySerializer(serializers.ModelSerializer):
    ROLE_CHOICES = (
        ('manager', _('Manager')),
        ('staff', _('Staff')),
        ('cleaner', _('Cleaner')),
        ('security', _('Security')),
        ('receptionist', _('Receptionist')),
    )

    salary_map = {
        'manager': 5000.00,
        'staff': 3000.00,
        'cleaner': 2000.00,
        'security': 2500.00,
        'receptionist': 3500.00,
    }

    description = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        error_messages={
            'max_length': _('Description cannot exceed 255 characters.')
        }
    )
    role_type = serializers.ChoiceField(
        choices=ROLE_CHOICES,
        error_messages={
            'invalid_choice': _('Invalid role type choice.'),
            'blank': _('Role type cannot be blank.')
        }
    )

    salary = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
        error_messages={
            'invalid': _('Salary must be a valid decimal number.'),
            'max_digits': _('Salary cannot exceed 10 digits.'),
            'decimal_places': _('Salary must have up to 2 decimal places.')
        }
    )
    
    

    class Meta:
        model = EmployeeRole
        fields = ['role_type', 'description', 'salary']

        #method to validate the role type and description
        def validate(self, attrs):
            role_type = attrs.get('role_type')
            description = attrs.get('description')

            if not role_type:
                raise serializers.ValidationError({'role_type': _('Role type is required.')})

            if not description:
                raise serializers.ValidationError({'description': _('Description is required.')})

            return attrs

    def create(self, validated_data):
        role_type = validated_data.get('role_type')
        salary = self.salary_map.get(role_type, 0.00)
        return EmployeeRole.objects.create(
            role_type=role_type,
            description=validated_data.get('description', ''),
            salary=salary
        )

    def update(self, instance, validated_data):
        role_type = validated_data.get('role_type', instance.role_type)
        description = validated_data.get('description', getattr(instance, 'description', ''))
        salary = self.salary_map.get(role_type, instance.salary)

        instance.role_type = role_type
        instance.description = description
        instance.salary = salary
        instance.save()
        return instance

# serializer to handle employee creation
class CreateEmployeeSerializer(serializers.ModelSerializer):
    ROLE_CHOICES = (
        ('manager', _('Manager')),
        ('staff', _('Staff')),
        ('cleaner', _('Cleaner')),
        ('security', _('Security')),
        ('receptionist', _('Receptionist')),
    )
    username = serializers.CharField(
        max_length=150,
        min_length=3,
        validators=[UnicodeUsernameValidator()],
        error_messages={
            'blank': _('Username cannot be blank.'),
            'max_length': _('Username cannot exceed 150 characters.'),
            'min_length': _('Username must be at least 3 characters long.')
        }
    )

    full_name = serializers.CharField(
        max_length=100,
        error_messages={
            'blank': _('Full name cannot be blank.'),
            'max_length': _('Full name cannot exceed 100 characters.')
        }
    )
    email = serializers.EmailField(
        error_messages={
            'blank': _('Email cannot be blank.'),
            'invalid': _('Enter a valid email address.')
        }
    )
    phone_number = serializers.CharField(
        max_length=15,
        error_messages={
            'blank': _('Phone number cannot be blank.'),
            'max_length': _('Phone number cannot exceed 15 characters.')
        }
    )

    role = serializers.SerializerMethodField()

    def get_role(self, obj):
        if obj.role:
            return {
                'role_type': obj.role.role_type,
                'salary': obj.role.salary,
                'description': obj.role.description
            }
        return {
            'role_type': _('Role cannot be blank.')
        }
        required=False,  # Role is optional during creation
        allow_null=True,# Allow null value for role
        
        
    
    
    class Meta:
        model = Employee
        fields = '__all__'
        
    #method to validate the username
    def validate_username(self, value):
        if Employee.objects.filter(username=value).exists():
            raise serializers.ValidationError(_('Username already exists.'))
        return value
    def validate(self, data):
        """Custom validation to ensure email and phone number are unique."""
        email = data.get('email')
        phone_number = data.get('phone_number')

        if Employee.objects.filter(email=email).exists():
            raise serializers.ValidationError({'email': _('Email already exists.')})

        if Employee.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError({'phone_number': _('Phone number already exists.')})

        return data
    
    def create(self, validated_data):
        """Create a new employee"""
        employee = Employee.objects.create(**validated_data)

        return employee
        #method to get the role salary of an employee
    
    def get_role_salary(self, obj):
        if obj.role:
            return {
                'role_type': obj.role.role_type,
                'salary_role': obj.role.salary_role,
                'description': obj.role.description
            }   