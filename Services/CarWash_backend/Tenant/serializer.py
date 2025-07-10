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
from decimal import Decimal

from .models import TenantProfile, Tenant, CarCheckIn, Task
from Staff.models import StaffProfile, StaffRole, Staff

# Import models to avoid circular import issues
def get_location_model():
    from Location.models import Location
    return Location

def get_booking_model():
    from booking.models import booking
    return booking

def get_location_service_model():
    from Location.models import LocationService
    return LocationService

# Enhanced TenantProfile Serializer with standardized response format
class TenantProfileSerializer(serializers.ModelSerializer):
    tenant = serializers.StringRelatedField(read_only=True)
    name = serializers.CharField(source='tenant.name', read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    image_tag = serializers.ReadOnlyField(read_only=True)
    total_staff = serializers.SerializerMethodField(read_only=True)
    total_locations = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TenantProfile
        fields = [
            'id', 'tenant', 'name', 'business_name', 'business_email', 'username',
            'first_name', 'last_name', 'logo', 'phone_number', 'address',
            'total_staff', 'total_locations', 'image_tag', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']

    def get_total_staff(self, obj):
        """Get total staff count for this tenant."""
        return StaffProfile.objects.filter(tenant=obj.tenant).count()

    def get_total_locations(self, obj):
        """Get total locations count for this tenant."""
        Location = get_location_model()
        return Location.objects.filter(tenant=obj.tenant).count()

    def validate(self, data):
        """Custom validation to ensure business email, business name and phone number are valid and unique."""
        phone_number = data.get('phone_number')
        business_email = data.get('business_email')
        
        # Validate business email domain
        if business_email and not business_email.endswith('@tenant.com'):
            raise serializers.ValidationError({
                'business_email': _('Business email must be a valid tenant email ending with @tenant.com.')
            })
        
        # Validate phone number format
        if phone_number and not phone_number.startswith('+254'):
            raise serializers.ValidationError({
                'phone_number': _('Phone number must be in international format starting with +254.')
            })
        
        return data

    def validate_business_name(self, value):
        """Validate that the business name is unique during creation but not during update."""
        if self.instance:
            # During update - only check if value has changed
            if self.instance.business_name == value:
                return value
            # Check uniqueness excluding current instance
            if TenantProfile.objects.filter(business_name__iexact=value).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError(_('Business name already exists.'))
        else:
            # During creation - check uniqueness across all profiles
            if TenantProfile.objects.filter(business_name__iexact=value).exists():
                raise serializers.ValidationError(_('Business name already exists.'))
        
        return value

    def create(self, validated_data):
        """Create a new tenant profile instance."""
        request = self.context.get('request')
        tenant = request.user if hasattr(request, 'user') and hasattr(request.user, 'tenant') else None
        if not tenant:
            raise ValidationError(_('Tenant must be authenticated.'))
        validated_data['tenant'] = tenant
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Update an existing tenant profile instance."""
        for field in ['business_name', 'business_email', 'username', 'first_name', 
                      'last_name', 'logo', 'phone_number', 'address']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()
        return instance

# Enhanced Tenant Login Serializer with better error handling
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

    def get_tenant_profile(self):
        """Return the tenant profile associated with the validated data."""
        tenant_profile = self.validated_data.get('tenant_profile')
        if tenant_profile:
            return {
                'id': tenant_profile.pk,
                'business_name': tenant_profile.business_name,
                'business_email': tenant_profile.business_email,
                'username': tenant_profile.username,
                'first_name': tenant_profile.first_name,
                'last_name': tenant_profile.last_name,
                'phone_number': tenant_profile.phone_number,
                'address': tenant_profile.address,
                'logo': tenant_profile.logo.url if tenant_profile.logo else None,
                'created_at': tenant_profile.created_at,
                'updated_at': tenant_profile.updated_at
            }
        return None
    
    def get_tenant(self):
        return self.validated_data.get('tenant', None)

# Enhanced Employee Role Salary Serializer
class EmployeeRoleSalarySerializer(serializers.ModelSerializer):
    ROLE_CHOICES = (
        ('manager', _('Manager')),
        ('staff', _('Staff')),
        ('cleaner', _('Cleaner')),
        ('security', _('Security')),
        ('receptionist', _('Receptionist')),
    )

    salary_map = {
        'manager': Decimal('50000.00'),
        'staff': Decimal('30000.00'),
        'cleaner': Decimal('20000.00'),
        'security': Decimal('25000.00'),
        'receptionist': Decimal('35000.00'),
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
        fields = ['id', 'role_type', 'description', 'salary', 'created_at', 'updated_at']
        read_only_fields = ['id', 'salary', 'created_at', 'updated_at']

    def validate(self, attrs):
        """Validate the role type and description."""
        role_type = attrs.get('role_type')
        if not role_type:
            raise serializers.ValidationError({'role_type': _('Role type is required.')})
        return attrs

    def create(self, validated_data):
        """Create a new staff role with auto-calculated salary."""
        role_type = validated_data.get('role_type')
        salary = self.salary_map.get(role_type, Decimal('0.00'))
        
        request = self.context.get('request')
        tenant = getattr(request, 'user', None)
        
        return StaffRole.objects.create(
            role_type=role_type,
            description=validated_data.get('description', ''),
            salary=salary,
            tenant=tenant
        )

    def update(self, instance, validated_data):
        """Update staff role with auto-calculated salary."""
        role_type = validated_data.get('role_type', instance.role_type)
        description = validated_data.get('description', instance.description)
        salary = self.salary_map.get(role_type, instance.salary)

        instance.role_type = role_type
        instance.description = description
        instance.salary = salary
        instance.save()
        return instance

# Enhanced Create Employee Serializer
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
        min_length=8,
        style={'input_type': 'password'},
        error_messages={
            'blank': _('Password cannot be blank.'),
            'min_length': _('Password must be at least 8 characters long.')
        }
    )

    role_id = serializers.PrimaryKeyRelatedField(
        source='role',
        queryset=StaffRole.objects.all(),
        write_only=True,
        error_messages={
            'does_not_exist': _('Role does not exist.'),
            'required': _('Role is required.')
        }
    )
    
    location_id = serializers.PrimaryKeyRelatedField(
        source='location',
        queryset=get_location_model().objects.none(),
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
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            tenant = request.user
            Location = get_location_model()
            
            self.fields['location_id'].queryset = Location.objects.filter(tenant=tenant)
            self.fields['role_id'].queryset = StaffRole.objects.filter(tenant=tenant)
        else:
            Location = get_location_model()
            self.fields['location_id'].queryset = Location.objects.none()
            self.fields['role_id'].queryset = StaffRole.objects.none()

    def get_role(self, obj):
        """Get role details."""
        if obj.role:
            return {
                'id': obj.role.id,
                'role_type': obj.role.role_type,
                'salary': str(obj.role.salary),
                'description': obj.role.description
            }
        return None

    def get_location(self, obj):
        """Get location details."""
        if obj.location:
            return {
                'id': obj.location.id,
                'name': obj.location.name,
                'address': obj.location.address
            }
        return None

    class Meta:
        model = Staff
        fields = [
            'id', 'username', 'email', 'password', 'first_name', 'last_name',
            'role_id', 'location_id', 'role', 'location', 'is_active',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
        }
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')
        
    def validate_username(self, value):
        """Validate username uniqueness."""
        if Staff.objects.filter(username=value).exists():
            raise serializers.ValidationError(_('Username already exists.'))
        return value

    def validate_email(self, value):
        """Validate email uniqueness."""
        if Staff.objects.filter(email=value).exists():
            raise serializers.ValidationError(_('Email already exists.'))
        return value

    def validate(self, data):
        """Custom validation."""
        # Check if the location belongs to the current tenant
        location = data.get('location')
        if location:
            request = self.context.get('request')
            tenant = getattr(request, 'user', None)
            if location.tenant != tenant:
                raise serializers.ValidationError({
                    'location_id': _('Location does not belong to the current tenant.')
                })
        
        # Check if role belongs to tenant
        role = data.get('role')
        if role:
            request = self.context.get('request')
            tenant = getattr(request, 'user', None)
            if role.tenant != tenant:
                raise serializers.ValidationError({
                    'role_id': _('Role does not belong to the current tenant.')
                })

        return data
    
    def create(self, validated_data):
        """Create a new employee."""
        request = self.context.get('request')
        tenant = getattr(request, 'user', None)
        validated_data['tenant'] = tenant
        
        employee = Staff.objects.create(**validated_data)
        return employee

# Enhanced Task Serializer
class TaskSerializer(serializers.ModelSerializer):
    assigned_to = serializers.CharField(source='assigned_to.username', read_only=True)
    location = serializers.CharField(source='location.name', read_only=True)
    tenant = serializers.CharField(source='tenant.name', read_only=True)
    booking_made = serializers.CharField(source='booking_made.booking_number', read_only=True)
    booking_location_service_services = serializers.SerializerMethodField(read_only=True)
    next_possible_status = serializers.SerializerMethodField(read_only=True)

    # Write only fields
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        source='assigned_to',
        queryset=StaffProfile.objects.none(),
        write_only=True,
        required=True
    )
    
    location_id = serializers.PrimaryKeyRelatedField(
        source='location',
        queryset=get_location_model().objects.none(),
        write_only=True,
        required=True
    )
    
    booking_id = serializers.PrimaryKeyRelatedField(
        source='booking_made',
        queryset=get_booking_model().objects.none(),
        write_only=True,
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            tenant = request.user
            Location = get_location_model()
            Booking = get_booking_model()

            self.fields['location_id'].queryset = Location.objects.filter(tenant=tenant)
            self.fields['booking_id'].queryset = Booking.objects.filter(location__tenant=tenant)
            self.fields['assigned_to_id'].queryset = StaffProfile.objects.filter(tenant=tenant)
    
    def get_next_possible_status(self, obj):
        """Return the next possible status for a task."""
        status_transitions = {
            'pending': ['in_progress', 'completed', 'overdue'],
            'in_progress': ['completed', 'overdue'],
            'completed': [],
            'overdue': ['completed']
        }
        return status_transitions.get(obj.status, [])

    def get_booking_location_service_services(self, obj):
        """Return the services in the booking location service."""
        if obj.booking_made and obj.booking_made.location_service:
            services = obj.booking_made.location_service.service.all()
            return [{'id': service.id, 'name': service.name, 'price': str(service.price)} for service in services]
        return []

    class Meta:
        model = Task
        fields = [
            'id', 'location', 'booking_made', 'description', 'tenant',
            'assigned_to', 'status', 'priority', 'due_date', 'assigned_to_id',
            'location_id', 'booking_id', 'booking_location_service_services', 
            'next_possible_status', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')

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

        return data

    def create(self, validated_data):
        """Create a new task instance."""
        if 'status' not in validated_data:
            validated_data['status'] = 'pending'
            
        request = self.context.get('request')
        tenant = getattr(request, 'user', None)
        validated_data['tenant'] = tenant
        
        task = Task.objects.create(**validated_data)
        return task

# Enhanced Dashboard Statistics Serializer
class TenantDashboardSerializer(serializers.Serializer):
    # Staff metrics
    total_staff = serializers.IntegerField(read_only=True)
    active_staff = serializers.SerializerMethodField(read_only=True)
    
    # Location metrics
    total_locations = serializers.IntegerField(read_only=True)
    
    # Task metrics
    total_tasks = serializers.IntegerField(read_only=True)
    pending_tasks = serializers.IntegerField(read_only=True)
    in_progress_tasks = serializers.IntegerField(read_only=True)
    completed_tasks = serializers.IntegerField(read_only=True)
    overdue_tasks = serializers.IntegerField(read_only=True)
    
    # Booking metrics
    total_bookings = serializers.IntegerField(read_only=True)
    confirmed_bookings = serializers.IntegerField(read_only=True)
    completed_bookings = serializers.IntegerField(read_only=True)
    
    # Financial metrics
    revenue_this_month = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    revenue_today = serializers.SerializerMethodField(read_only=True)
    
    # Performance metrics
    task_completion_rate = serializers.SerializerMethodField(read_only=True)
    booking_success_rate = serializers.SerializerMethodField(read_only=True)

    def get_active_staff(self, data):
        """Calculate active staff count."""
        return data.get('total_staff', 0)  # Assuming all staff are active

    def get_revenue_today(self, data):
        """Calculate today's revenue."""
        from datetime import date
        from django.db.models import Sum
        
        Booking = get_booking_model()
        today_revenue = Booking.objects.filter(
            location__tenant=self.context['tenant'],
            status='completed',
            created_at__date=date.today()
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        
        return today_revenue

    def get_task_completion_rate(self, data):
        """Calculate task completion rate."""
        total = data.get('total_tasks', 0)
        completed = data.get('completed_tasks', 0)
        return round((completed / total * 100), 2) if total > 0 else 0

    def get_booking_success_rate(self, data):
        """Calculate booking success rate."""
        total = data.get('total_bookings', 0)
        completed = data.get('completed_bookings', 0)
        return round((completed / total * 100), 2) if total > 0 else 0

# Car Check-in Items Serializer
class CarCheckInItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarCheckIn
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')
