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
from django.contrib.auth.hashers import check_password

from .models import TenantProfile, Tenant, CarCheckIn, Task
from Staff.models import StaffProfile, StaffRole, Staff
# Import models to avoid circular import issues
def get_location_model():
    from Location.models import Location
    return Location

def get_booking_model():
    from booking.models import Booking
    return Booking

def get_location_service_model():
    from Location.models import LocationService
    return LocationService

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
        tenant = request.user if hasattr(request, 'user') and hasattr(request.user, 'tenant') else None
        if not tenant:
            raise ValidationError(_('Tenant must be set.'))
        validated_data['tenant'] = tenant
        return super().create(validated_data)

    #serializer method to handle  tenant existing profile update
    def update(self, instance, validated_data):
        """Update an existing tenant profile instance."""
        for field in ['business_name', 'business_email', 'username', 'first_name', 
                      'last_name', 'logo', 'phone_number', 'address']:
            setattr(instance, field, validated_data.get(field, getattr(instance, field)))
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
        tenant_profile = self.validated_data.get('tenant_profile')
        if tenant_profile:
            return {
                'id': tenant_profile.pk,
                'business_name': tenant_profile.business_name,
                'business_email': tenant_profile.business_email,
                'phone_number': tenant_profile.phone_number,
                'address': tenant_profile.address,
                'created_at': tenant_profile.created_at,
                'updated_at': tenant_profile.updated_at
            }
        return None
    
    def get_tenant(self):
        return self.validated_data.get('tenant', None)

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

            return attrs

    def create(self, validated_data):
        role_type = validated_data.get('role_type')
        salary = self.salary_map.get(role_type, 0.00)
        
        request = self.context.get('request')
        tenant = getattr(request, 'user', None)
        
        return StaffRole.objects.create(
            role_type=role_type,
            description=validated_data.get('description', ''),
            salary=salary,
            tenant=tenant
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

# Serializer to handle employee creation
class CreateEmployeeSerializer(serializers.ModelSerializer):
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
        queryset=StaffRole.objects.all(),  # Show all roles since StaffRole doesn't have tenant field
        write_only=True,
        error_messages={
            'does_not_exist': _('Role does not exist.'),
            'required': _('Role is required.')
        }
    )
    
    location_id = serializers.PrimaryKeyRelatedField(
        source='location',
        queryset=get_location_model().objects.none(),  # Will be set in __init__
        write_only=True,
        error_messages={
            'does_not_exist': _('Location does not exist.'),
            'required': _('Location is required.')
        }
    )
 
    role = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set querysets dynamically based on request context
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            tenant = request.user
            Location = get_location_model()
            
            # Set the queryset for location_id field - filter by tenant
            self.fields['location_id'].queryset = Location.objects.filter(tenant=tenant)
            # StaffRole doesn't have tenant field, so we show all roles
            self.fields['role_id'].queryset = StaffRole.objects.all()
        else:
            # Fallback to empty querysets if no request context
            Location = get_location_model()
            self.fields['location_id'].queryset = Location.objects.none()
            self.fields['role_id'].queryset = StaffRole.objects.none()

    def get_role(self, obj):
        if obj.role:
            return {
                'role_type': obj.role.role_type,
                'salary': obj.role.salary,
                'description': obj.role.description
            }
        return None

    def get_location(self, obj):
        if obj.location:
            return {
                'id': obj.location.id,
                'name': obj.location.name
            }
        return None

    class Meta:
        model = Staff
        fields = [
            'id', 'username', 'email', 'password',
            'role_id', 'location_id', 'role', 'location'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
        }
        read_only_fields = ('tenant', 'created_at', 'updated_at')
        
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
        
        # Check if the location belongs to the current tenant
        location = data.get('location')
        if location:
            request = self.context.get('request')
            tenant = getattr(request, 'user', None)
            if location.tenant != tenant:
                raise serializers.ValidationError({
                    'location_id': _('Location does not belong to the current tenant.')
                })

        return data
    
    def create(self, validated_data):
        """Create a new employee"""
        request = self.context.get('request')
        tenant = getattr(request, 'user', None)
        validated_data['tenant'] = tenant
        
        employee = Staff.objects.create(**validated_data)
        return employee

# serializer to handle car check in
class CarCheckInItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarCheckIn
        fields = '__all__'
        read_only_fields = ('tenant', 'created_at', 'updated_at')

# Task Serializer
class TaskSerializer(serializers.ModelSerializer):
    assigned_to = serializers.CharField(source='assigned_to.username', read_only=True)
    location = serializers.CharField(source='location.name', read_only=True)
    tenant = serializers.CharField(source='tenant.name', read_only=True)
    booking_made = serializers.CharField(source='booking_made.id', read_only=True)
    booking_location_service_services = serializers.SerializerMethodField(read_only=True)
    checkin_items = CarCheckInItemsSerializer(read_only=True, many=True)
    next_possible_status = serializers.SerializerMethodField(read_only=True)

    # Write only fields
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        source='assigned_to',
        queryset=StaffProfile.objects.none(),  # Will be set in __init__
        write_only=True,
        required=True
    )
    
    location_id = serializers.PrimaryKeyRelatedField(
        source='location',
        queryset=get_location_model().objects.none(),  # Will be set in __init__
        write_only=True,
        required=True
    )
    
    booking_id = serializers.PrimaryKeyRelatedField(
        source='booking_made',
        queryset=get_booking_model().objects.none(),  # Will be set in __init__
        write_only=True,
        required=True
    )
    
    checkin_items_data = CarCheckInItemsSerializer(
        source='car_checkins',
        many=True,
        write_only=True,
        required=False,
        error_messages={
            'blank': _('Check-in items cannot be blank.'),
        }
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            tenant = request.user
            Location = get_location_model()
            Booking = get_booking_model()
            
            self.fields['location_id'].queryset = Location.objects.filter(tenant=tenant)
            self.fields['booking_id'].queryset = Booking.objects.filter(tenant=tenant)
            # Filter StaffProfile by tenant field
            self.fields['assigned_to_id'].queryset = StaffProfile.objects.filter(tenant=tenant)
        else:
            # Fallback to empty querysets
            Location = get_location_model()
            Booking = get_booking_model()
            self.fields['location_id'].queryset = Location.objects.none()
            self.fields['booking_id'].queryset = Booking.objects.none()
            self.fields['assigned_to_id'].queryset = StaffProfile.objects.none()
    
    def get_next_possible_status(self, obj):
        """Return the next possible status for a task."""
        status_transitions = {
            'pending': ['in_progress', 'completed', 'overdue'],
            'in_progress': ['completed', 'overdue'],
            'completed': [],
            'overdue': []
        }
        return status_transitions.get(obj.status, [])

    def get_booking_location_service_services(self, obj):
        """Return the services in the booking location service."""
        if obj.booking_made and obj.booking_made.location_service:
            services = obj.booking_made.location_service.service.all()
            return [service.name for service in services]
        return []

    class Meta:
        model = Task
        fields = [
            'id', 'location', 'booking_made', 'description', 'tenant', 'checkin_items_data', 
            'checkin_items', 'assigned_to', 'status', 'priority', 'due_date', 'assigned_to_id',
            'location_id', 'booking_id', 'booking_location_service_services', 'next_possible_status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('tenant', 'created_at', 'updated_at')

    def validate(self, data):
        """Validate task creation."""
        booking = data.get('booking_made')
        if booking and booking.status not in ['confirmed', 'completed']:
            raise serializers.ValidationError({
                'booking_made': _('Booking must be confirmed or completed to assign a task.')
            })
        
        assigned_to = data.get('assigned_to')
        if assigned_to:
            request = self.context.get('request')
            tenant = getattr(request, 'user', None)
            if assigned_to.tenant != tenant:
                raise serializers.ValidationError({
                    'assigned_to_id': _('You can only assign tasks to your own staff.')
                })
        
        # Check if task with this booking already exists
        Task = self.Meta.model
        if Task.objects.filter(booking_made=booking).exists():
            raise serializers.ValidationError({
                'booking_made': _('Task with this booking already exists.')
            })

        return data

    def create(self, validated_data):
        """Create a new task instance."""
        booking = validated_data.pop('booking_made', None)
        checkin_items_data = validated_data.pop('car_checkins', [])
        
        # Set default status to 'pending' when creating a new task
        if 'status' not in validated_data:
            validated_data['status'] = 'pending'
            
        request = self.context.get('request')
        tenant = getattr(request, 'user', None)
        validated_data['tenant'] = tenant
        
        task = Task.objects.create(**validated_data)
        if booking:
            task.booking_made = booking
            task.save()
            
        # Create CarCheckIn instances
        for item_data in checkin_items_data:
            CarCheckIn.objects.create(task=task, tenant=tenant, **item_data)

        return task

# Dashboard Statistics Serializer
class TenantDashboardSerializer(serializers.Serializer):
    total_staff = serializers.IntegerField(read_only=True)
    total_locations = serializers.IntegerField(read_only=True)
    total_tasks = serializers.IntegerField(read_only=True)
    pending_tasks = serializers.IntegerField(read_only=True)
    in_progress_tasks = serializers.IntegerField(read_only=True)
    completed_tasks = serializers.IntegerField(read_only=True)
    overdue_tasks = serializers.IntegerField(read_only=True)
    total_bookings = serializers.IntegerField(read_only=True)
    confirmed_bookings = serializers.IntegerField(read_only=True)
    completed_bookings = serializers.IntegerField(read_only=True)
    revenue_this_month = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
