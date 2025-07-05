
from ctypes import FormatError
from email import message
from os import read, write
import re
from tabnanny import check
from urllib import request
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db.models import Q

from Tenant.models import TenantProfile, Tenant
from django.contrib.auth.hashers import check_password
from Staff.models import StaffProfile, StaffRole,Staff
from .models import CarCheckIn, Task, Location



# TenantProfile Serializer
class TenantProfileSerializer(serializers.ModelSerializer):
    tenant = serializers.StringRelatedField(read_only=True)
    name = serializers.CharField(source='tenant.name', read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    image_tag = serializers.ReadOnlyField(read_only=True)

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
    # this is to ensure that the business name is unique across all tenant profiles
    # during update of tenant profile, we do not check if the business name is already taken
    
    def validate_business_name(self, value):
        """Validate that the business name is unique. during creation of tenant profile. but not during update."""
        if self.instance:
            # if no change, return the existing value
            if self.instance.business_name == value:
            # No change in business name, so we can safely return the existing value
                return value
        # Check if the business name already exists in other tenant profiles
        if TenantProfile.objects.filter(business_name__iexact=value).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError(_('Business name already exists.'))
        # This check is only performed during creation of tenant profile
        
            return value
        if TenantProfile.objects.filter(business_name__iexact=value).exists():
            raise serializers.ValidationError(_('Business name already exists.'))
        return value

# perform update method to ensure that the tenant profile is updated correctly
   
    def create(self, validated_data):
        """Create a new tenant profile instance."""
        request = self.context.get('request')
        tenant = request.tenant if hasattr(request, 'tenant') else None
        if not tenant:
            raise ValidationError(_('Tenant must be set.'))
        validated_data['tenant'] = tenant
        return super().create(validated_data)

    #serializer method to handle  tenant existing profile update
    def update(self, instance, validated_data):
        """Update an existing tenant profile instance."""
        instance.business_name = validated_data.get('business_name', instance.business_name)
        instance.business_email = validated_data.get('business_email', instance.business_email)
        instance.username = validated_data.get('username', instance.username)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.logo = validated_data.get('logo', instance.logo)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.address = validated_data.get('address', instance.address)
        instance.save()
        return instance

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
        return f"Tenant Profile for {tenant.name}"

    
    def get_tenant(self):
       return self.validated_data.get('tenant', None)

    # method to return the tenant profile




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
        model = StaffRole
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
        return StaffRole.objects.create(
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

   
    email = serializers.EmailField(
        error_messages={
            'blank': _('Email cannot be blank.'),
            'invalid': _('Enter a valid email address.')
        }
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

    email = serializers.EmailField(
        error_messages={
            'blank': _('Email cannot be blank.'),
            'invalid': _('Enter a valid email address.')
        }
    )

    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        error_messages={
            'blank': _('Password cannot be blank.'),
        }
    )

    role_id = serializers.PrimaryKeyRelatedField(
        source='role',
        queryset=StaffRole.objects.all(),
        write_only=True,  # Make role write-only for creation
        error_messages={
            'does_not_exist': _('Role does not exist.'),
            'required': _('Role is required.')
        }
    )
    location_id = serializers.PrimaryKeyRelatedField(
        source='location',
        queryset=Location.objects.all(),
        write_only=True,  # Make location write-only for creation
        error_messages={
            'does_not_exist': _('Location does not exist.'),
            'required': _('Location is required.')
        }
    )
 
    role = serializers.SerializerMethodField()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure that role is not required during creation
        request = self.context.get('request')
        if request and hasattr(request, 'tenant'):
            self.fields['location_id'].queryset = Location.objects.filter(tenant=request.tenant)

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
        
    location = serializers.SerializerMethodField()

    def get_location(self, obj):
        if obj.location:
            return {
                'id': obj.location.id,
                'name': obj.location.name
            }
        return None

    class Meta:
        model = Staff
        fields = '__all__'
        read_only_fields = ('tenant', 'created_at', 'updated_at', 'is_active')
        
    #method to validate the username
    def validate_username(self, value):
        if Staff.objects.filter(username=value).exists():
            raise serializers.ValidationError(_('Username already exists.'))
        return value
    def validate(self, data):
        """Custom validation to ensure email and phone number are unique."""
        password = data.get('password')
        if not password:
            raise serializers.ValidationError({'password': _('Password is required.')})
        email = data.get('email')
       

        if Staff.objects.filter(email=email).exists():
            raise serializers.ValidationError({'email': _('Email already exists.')})
        
        #check if the location_id if for the login tenant
        location_id = data.get('location_id')
        if location_id:
            tenant = self.context['request'].tenant
            if not TenantProfile.objects.filter(id=location_id, tenant=tenant).exists():
                raise serializers.ValidationError({'location_id': _('Location does not belong to the current tenant.')})

        

        return data
    
    def create(self, validated_data):
        """Create a new employee"""
        employee = Staff.objects.create(**validated_data)

        return employee
    
        #method to get the role salary of an employee
    
    def get_role_salary(self, obj):
        if obj.role:
            return {
                'role_type': obj.role.role_type,
                'salary_role': obj.role.salary_role,
                'description': obj.role.description
            }   
            
            
#class serializer to handle  task creation
from booking.serializer import BookingSerializer
from Location.serializer import LocationSerializer, LocationServiceSerializer
from Staff.serializer import StaffProfileSerializer
from .models import Task, Location, Booking, CarCheckIn

   
#serializer to hanle car check in
class CarCheckInItemsSerializer(serializers.ModelSerializer):
    from .models import CarCheckIn
    class Meta:
        model = CarCheckIn
        fields = '__all__ '
        read_only_fields = ('tenant', 'created_at', 'updated_at')

class TaskSerializer(serializers.ModelSerializer):
    #read_only_fields = ('tenant', 'location', 'created_at', 'updated_at')
    assigned_to = serializers.CharField(source='assigned_to.username', read_only=True)
    location = serializers.CharField(source='location.name', read_only=True)
    tenant = serializers.CharField(source='tenant.name', read_only=True)
    booking_made = serializers.CharField(source='booking_made.id', read_only=True)
    booking_location_service_services = serializers.SerializerMethodField(read_only=True)  # <-- Add this line
    checkin_items = CarCheckInItemsSerializer(read_only=True, many=True)#read only field for car check in items nnested from child serializer 

#write only fields
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        source='assigned_to',
        queryset=StaffProfile.objects.all(),
        write_only=True,
        required=True  # Make assigned_to_id required for task creation
    )
    location_id = serializers.PrimaryKeyRelatedField(
        source='location',
        queryset=Location.objects.all(),
        write_only=True,
        required=True
    )
    booking_id = serializers.PrimaryKeyRelatedField(
        source='booking_made',
        queryset=Booking.objects.all(),
        write_only=True,
        required=True  # Make booking_id required for task creation
    )
    checkin_items_data = CarCheckInItemsSerializer(
        source='car_checkins',
        many=True,
        write_only=True,
        required=False,  # Make checkin_items_data optional for task creation
        error_messages={
            'blank': _('Check-in items cannot be blank.'),
            'required': _('Check-in items are required.')
        }
        
    )
    #display booking names in more readable format
    booking_location_service = serializers.SerializerMethodField(read_only=True)
    def get_booking_location_service(self, obj):
        """Return the booking name for display purposes."""
        if obj.booking_made:
            return {
                'booking_id': obj.booking_made.id,
                'booking_location_service': obj.booking_made.location_service.name if obj.booking_made.location_service else None,
                'booking_location': obj.booking_made.location.name if obj.booking_made.location else None
                }
            
        return None
    
    #method to get services in location_service
    def get_booking_location_service_services(self, obj):
        """return the services in the booking location service."""
        if obj.booking_made and obj.booking_made.location_service:
            service = obj.booking_made.location_service.service.all()
            if service is not None:
                return [service.name for service in service]
        return []

    class Meta:
        model = Task
        fields = [
            'location', 'booking_made', 'description','tenant', 'checkin_items_data', 'checkin_items',
            'assigned_to', 'status', 'priority', 'due_date', 'assigned_to_id',
            'location_id', 'booking_id',
            'booking_location_service', 'booking_location_service_services'
        ]
        write_only_fields = ('assigned_to_id', 'location_id', 'booking_id')
        read_only_fields = ('tenant', 'created_at', 'updated_at')

    def validate(self, data):
        #task can only be assigned if the booking status is confirmed or completed
        booking = data.get('booking_made')
        if booking and booking.status != 'confirmed' and booking.status != 'completed':
            raise serializers.ValidationError({'booking_made': _('Booking must be confirmed or completed to assign a task.')})
        #check if the assigned_to_id is for the login tenant
        assigned_to_id = data.get('assigned_to_id')
        if assigned_to_id and assigned_to_id.tenant != self.context['request'].user.tenant:
            raise serializers.ValidationError({'assigned_to_id': _('You can only assign tasks to your own staff.')})
        #check if the task with the booking_made has been assigned
        if Task.objects.filter(booking_made=data.get('booking_made'), assigned_to=assigned_to_id).exists():
            assigned_to = StaffProfile.objects.get(id=assigned_to_id)
            raise serializers.ValidationError({'booking_made': _('Task with this booking has already been assigned to another staff member {assigned_to}.').format(assigned_to=assigned_to.username)})

        #check if there is task with the same booking_made
        if Task.objects.filter(booking_made=data.get('booking_made')).exists():
            raise serializers.ValidationError({'booking_made': _('Task with this booking already exists.')})
        

        return data

    def create(self, validated_data):
        
       """Create a new task instance."""
       booking = validated_data.pop('booking_made', None)
       checkin_items_data = validated_data.pop('checkin_items_data', [])
       
       task = Task.objects.create(**validated_data)
       task.booking_made.set(booking)

       # Create CarCheckIn instances
       for item_data in checkin_items_data:
           CarCheckIn.objects.create(task=task, **item_data)

       return task
