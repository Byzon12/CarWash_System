from importlib.util import source_from_cache
from os import read, write
import re
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from Staff.models import StaffProfile, StaffRole
from django.contrib.auth.hashers import check_password
from Location.models import Location, Service, LocationService
from decimal import Decimal
from .models import Favorite

# Enhanced serializer for location creation with better mobile support
class LocationSerializer(serializers.ModelSerializer):
    """
    Enhanced serializer for creating a new location with Flutter mobile support.
    """
    # Core location fields
    name = serializers.CharField(
        max_length=255, 
        required=True, 
        help_text=_("Name of the location"),
        error_messages={
            'required': 'Location name is required',
            'blank': 'Location name cannot be empty',
            'max_length': 'Location name cannot exceed 255 characters'
        }
    )
    address = serializers.CharField(
        max_length=255, 
        required=True, 
        help_text=_("Address of the location"),
        error_messages={
            'required': 'Address is required',
            'blank': 'Address cannot be empty'
        }
    )
    latitude = serializers.FloatField(
        required=True, 
        help_text=_("Latitude of the location"),
        min_value=-90.0,
        max_value=90.0,
        error_messages={
            'required': 'Latitude is required',
            'min_value': 'Latitude must be between -90 and 90',
            'max_value': 'Latitude must be between -90 and 90'
        }
    )
    longitude = serializers.FloatField(
        required=True, 
        help_text=_("Longitude of the location"),
        min_value=-180.0,
        max_value=180.0,
        error_messages={
            'required': 'Longitude is required',
            'min_value': 'Longitude must be between -180 and 180',
            'max_value': 'Longitude must be between -180 and 180'
        }
    )
    contact_number = serializers.CharField(
        max_length=20, 
        required=True, 
        allow_blank=False, 
        help_text=_("Contact number of the location (must start with +254)"),
        error_messages={
            'required': 'Contact number is required',
            'blank': 'Contact number cannot be empty'
        }
    )
    email = serializers.EmailField(
        required=False, 
        allow_blank=True, 
        help_text=_("Email address of the location"),
        error_messages={
            'invalid': 'Enter a valid email address'
        }
    )
    
    # Read-only fields for mobile display
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    total_services = serializers.SerializerMethodField(read_only=True)
    total_location_services = serializers.SerializerMethodField(read_only=True)
    is_active = serializers.SerializerMethodField(read_only=True)
    created_at_formatted = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Location
        fields = [
            "id", "name", "address", "latitude", "longitude", 
            "contact_number", "email", "tenant_name", "total_services",
            "total_location_services", "is_active", "created_at", 
            "updated_at", "created_at_formatted"
        ]
        read_only_fields = ["id", "created_at", "updated_at", "tenant"]
        
    def get_total_services(self, obj):
        """Get total number of services available for this location's tenant."""
        return obj.tenant.services.count() if obj.tenant else 0
    
    def get_total_location_services(self, obj):
        """Get total number of service packages for this location."""
        return obj.location_services.count()
    
    def get_is_active(self, obj):
        """make sure location is active by default"""
        return obj.is_active if hasattr(obj, 'is_active') else True
    
    def get_created_at_formatted(self, obj):
        """Format created_at for mobile display."""
        return obj.created_at.strftime("%Y-%m-%d %H:%M") if obj.created_at else None

    def validate_contact_number(self, value):
        """Validate Kenya phone number format."""
        if not value.startswith("+254"):
            raise serializers.ValidationError(_("Contact number must start with +254"))
        
        # Remove +254 and check remaining digits
        remaining = value[4:]
        if not remaining.isdigit() or len(remaining) != 9:
            raise serializers.ValidationError(_("Invalid phone number format. Use +254XXXXXXXXX"))
        
        return value
    
    def validate_name(self, value):
        """Validate location name uniqueness per tenant."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError(_("Location name cannot be empty"))
        return value

    def validate(self, data):
        """Enhanced validation for location data."""
        tenant = self.context.get('tenant')
        if not tenant:
            raise serializers.ValidationError(_("Tenant context is required"))
        
        name = data.get('name', '').strip()
        address = data.get('address', '').strip()
        
        # Check name uniqueness
        if Location.objects.filter(name__iexact=name, tenant=tenant).exists():
            raise serializers.ValidationError({
                'name': _("Location with this name already exists for your account")
            })
        
        # Check address uniqueness
        if Location.objects.filter(address__iexact=address, tenant=tenant).exists():
            raise serializers.ValidationError({
                'address': _("Location with this address already exists for your account")
            })
        
        return data

    def create(self, validated_data):
        """Create location with proper tenant assignment."""
        tenant = self.context.get('tenant')
        if not tenant:
            raise serializers.ValidationError(_("Tenant is required"))
        
        return Location.objects.create(tenant=tenant, **validated_data)

# Enhanced location update serializer
class LocationUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating an existing location with Flutter support.
    
    This serializer includes additional validation and read-only fields for mobile display.
    
    """
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    latitude = serializers.FloatField(required=False, min_value=-90.0, max_value=90.0)
    longitude = serializers.FloatField(required=False, min_value=-180.0, max_value=180.0)
    contact_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    
    # Read-only display fields
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    total_services = serializers.SerializerMethodField(read_only=True)
    total_location_services = serializers.SerializerMethodField(read_only=True)
    last_updated = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Location
        fields = [
            "id", "name", "address", "latitude", "longitude", 
            "contact_number", "email", "tenant_name", "total_services",
            "total_location_services", "last_updated", "updated_at"
        ]
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]
    
    def get_total_services(self, obj):
        return obj.tenant.services.count() if obj.tenant else 0
    
    def get_total_location_services(self, obj):
        return obj.location_services.count()
    
    def get_last_updated(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d %H:%M") if obj.updated_at else None

    def validate_contact_number(self, value):
        """Validate Kenya phone number format."""
        if value and not value.startswith("+254"):
            raise serializers.ValidationError(_("Contact number must start with +254"))
        return value

    def validate(self, data):
        """Enhanced validation for updates."""
        instance = self.instance
        if not instance:
            raise serializers.ValidationError(_("Location instance is required"))
        
        # Check name uniqueness if being updated
        name = data.get('name')
        if name and name.strip():
            name = name.strip()
            if Location.objects.filter(
                name__iexact=name, 
                tenant=instance.tenant
            ).exclude(id=instance.id).exists():
                raise serializers.ValidationError({
                    'name': _("Location with this name already exists for your account")
                })
        
        # Check address uniqueness if being updated
        address = data.get('address')
        if address and address.strip():
            address = address.strip()
            if Location.objects.filter(
                address__iexact=address, 
                tenant=instance.tenant
            ).exclude(id=instance.id).exists():
                raise serializers.ValidationError({
                    'address': _("Location with this address already exists for your account")
                })
        
        return data

# Enhanced service serializer
class ServiceSerializer(serializers.ModelSerializer):
    """
    Enhanced serializer for car wash services with mobile support.
    """
    name = serializers.CharField(
        max_length=255, 
        required=True,
        error_messages={
            'required': 'Service name is required',
            'blank': 'Service name cannot be empty'
        }
    )
    price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=True,
        min_value=Decimal('0.00'),
        error_messages={
            'required': 'Service price is required',
            'min_value': 'Price cannot be negative'
        }
    )
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        max_length=1000
    )
    
    # Read-only fields for mobile display
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    price_formatted = serializers.SerializerMethodField(read_only=True)
    is_active = serializers.SerializerMethodField(read_only=True, default=True)
    usage_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Service
        fields = [
            "id", "name", "price", "description", "tenant_name", 
            "price_formatted", "is_active", "usage_count"
        ]
        read_only_fields = ["id", "tenant"]
    
    def get_price_formatted(self, obj):
        """Format price for mobile display."""
        return f"KSh {obj.price:,.2f}" if obj.price else "KSh 0.00"
    
    def get_is_active(self, obj):
        """Ensures that the service is active by default."""
        return obj.is_active if hasattr(obj, 'is_active') else True
    
    def get_usage_count(self, obj):
        """Count how many location services use this service."""
        return obj.location_services.count()

    def validate_name(self, value):
        """Validate service name."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError(_("Service name cannot be empty"))
        return value

    def validate(self, data):
        """Enhanced validation for service data."""
        tenant = self.context.get('tenant')
        if not tenant:
            raise serializers.ValidationError(_("Tenant context is required"))
        
        name = data.get('name', '').strip()
        
        # Check name uniqueness per tenant
        existing_query = Service.objects.filter(name__iexact=name, tenant=tenant)
        if self.instance:
            existing_query = existing_query.exclude(id=self.instance.id)
        
        if existing_query.exists():
            raise serializers.ValidationError({
                'name': _("Service with this name already exists for your account")
            })
        
        return data

    def create(self, validated_data):
        """Create service with proper tenant assignment."""
        tenant = self.context.get('tenant')
        if not tenant:
            raise serializers.ValidationError(_("Tenant is required"))
        
        return Service.objects.create(tenant=tenant, **validated_data)

# Enhanced location service serializer
class LocationServiceSerializer(serializers.ModelSerializer):
    """
    Enhanced serializer for location service packages with comprehensive mobile support.
    """
    # Display fields (read-only)
    location_name = serializers.CharField(source='location.name', read_only=True)
    location_address = serializers.CharField(source='location.address', read_only=True)
    service_names = serializers.SerializerMethodField(read_only=True)
    service_details = ServiceSerializer(source='service', many=True, read_only=True)
    price = serializers.SerializerMethodField(read_only=True)
    price_formatted = serializers.SerializerMethodField(read_only=True)
    duration_formatted = serializers.SerializerMethodField(read_only=True)
    service_count = serializers.SerializerMethodField(read_only=True, help_text=_("Number of services in this package"))
    created_at_formatted = serializers.SerializerMethodField(read_only=True)
    
    # Write fields for creation/update
    location_id = serializers.PrimaryKeyRelatedField(
        source='location',
        queryset=Location.objects.none(),# set in __init__
        help_text=_("ID of the location for this service package"),
        write_only=True,
        required=True,
        error_messages={
            'required': 'Location is required',
            'does_not_exist': 'Selected location does not exist'
        }
    )
    service_ids = serializers.PrimaryKeyRelatedField(
        source='service',
        queryset=Service.objects.all(),# set in __init__
        write_only=True,
        help_text=_("List of service IDs included in this package"),
        many=True,
        required=True,
        error_messages={
            'required': 'At least one service must be selected',
            'does_not_exist': 'One or more selected services do not exist'
        }
    )
    
    # Core package fields
    name = serializers.CharField(
        max_length=255, 
        required=True,
        error_messages={
            'required': 'Package name is required',
            'blank': 'Package name cannot be empty'
        }
    )
    duration = serializers.DurationField(
        required=True,
        error_messages={
            'required': 'Duration is required',
            'invalid': 'Enter a valid duration (HH:MM:SS format)'
        }
    )
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        max_length=1000
    )

    class Meta:
        model = LocationService
        fields = [
            'id', 'name', 'description', 'duration', 'duration_formatted',
            'location_id', 'location_name', 'location_address',
            'service_ids', 'service_names', 'service_details', 'service_count',
            'price', 'price_formatted', 'created_at', 'created_at_formatted'
        ]
        read_only_fields = ["id", 'created_at', "updated_at"]
        
    def __init__(self, *args, **kwargs):
        """Initialize with proper tenant filtering."""
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            tenant = request.user
            self.fields['service_ids'].queryset = Service.objects.filter(tenant=tenant)
            self.fields['location_id'].queryset = Location.objects.filter(tenant=tenant)
        else:
            self.fields['service_ids'].queryset = Service.objects.none()
            self.fields['location_id'].queryset = Location.objects.none()

    def get_service_names(self, obj):
        """Get comma-separated service names."""
        return ", ".join([service.name for service in obj.service.all()])
    
    def get_price(self, obj):
        """Calculate total price from all services."""
        return sum(service.price or Decimal('0.00') for service in obj.service.all())
    
    def get_price_formatted(self, obj):
        """Format total price for mobile display."""
        total = self.get_price(obj)
        return f"KSh {total:,.2f}"
    
    def get_duration_formatted(self, obj):
        """Format duration for mobile display."""
        if obj.duration:
            total_seconds = int(obj.duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            if hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        return "0m"
    
    def get_service_count(self, obj):
        """Get number of services in package."""
        return obj.service.count()
    
    def get_created_at_formatted(self, obj):
        """Format creation date for mobile display."""
        return obj.created_at.strftime("%Y-%m-%d %H:%M") if obj.created_at else None

    def validate_name(self, value):
        """Validate package name."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError(_("Package name cannot be empty"))
        return value

    def validate(self, data):
        """Enhanced validation for location service packages."""
        request = self.context.get('request')
        tenant = request.user if request and request.user.is_authenticated else None
        
        if not tenant:
            raise serializers.ValidationError(_("Authentication required"))
        
        # Validate location belongs to tenant
        location = data.get('location')
        if location and location.tenant != tenant:
            raise serializers.ValidationError({
                'location_id': _("Selected location does not belong to your account")
            })
        
        # Validate services belong to tenant
        services = data.get('service', [])
        if not services:
            raise serializers.ValidationError({
                'service': _("At least one service must be selected")
            })
        
        for service in services:
            if service.tenant != tenant:
                raise serializers.ValidationError({
                    'service': _("All services must belong to your account")
                })
        
        # Check package name uniqueness per location
        name = data.get('name', '').strip()
        if name and location:
            existing_query = LocationService.objects.filter(
                name__iexact=name, 
                location=location
            )
            if self.instance:
                existing_query = existing_query.exclude(id=self.instance.id)
            
            if existing_query.exists():
                raise serializers.ValidationError({
                    'name': _("Package with this name already exists for this location")
                })
        
        return data

    def create(self, validated_data):
        """Create location service package."""
        services = validated_data.pop('service', [])
        
        if not services:
            raise serializers.ValidationError(_("At least one service must be selected"))
        
        try:
            
            location_service = LocationService.objects.create(**validated_data)
            #setting many to many relationship
            location_service.service.set(services)
            return location_service
        except Exception as e:
            raise serializers.ValidationError({
                'non-field_errors': [f"Error creating location services: {str(e)}"]
            })
    
    def update(self, instance, validated_data):
        """Update location service package."""
        services = validated_data.pop('service', None)
        
        # Update basic fields
        for field, value in validated_data.items():
            setattr(instance, field, value)
        
        instance.save()
        
        # Update services if provided
        if services is not None:
            instance.service.set(services)
        
        return instance


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ['id', 'user', 'location', 'created_at']