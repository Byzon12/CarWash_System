

from importlib.util import source_from_cache
from os import read
import re
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from Staff.models import StaffProfile, StaffRole, CarCheckInItem
from django.contrib.auth.hashers import check_password
from Location.models import Location, Service, LocationService

#serializer to handle location creation based on tenant
class LocationSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new location.
    """
    name = serializers.CharField(max_length=255, required=True, help_text=_("Name of the location"))
    address = serializers.CharField(max_length=255, required=True, help_text=_("Address of the location"))
    latitude = serializers.FloatField(required=True, help_text=_("Latitude of the location"))
    longitude = serializers.FloatField(required=True, help_text=_("Longitude of the location"))
    contact_number = serializers.CharField(max_length=20, required=True, allow_blank=True, help_text=_("Contact number of the location"))
    email = serializers.EmailField(required=True, allow_blank=True, help_text=_("Email address of the location"))
    
    class Meta:
        model = Location
        fields = ["name", "address", "latitude", "longitude", "contact_number", "email", 'id']
        read_only_fields = ["created_at", "updated_at", "tenant", "id"]
        
    #method to check if there is a another name the same to this

    def validate(self, data):
        """validate the data before creating a new location."""
        # Check if a location with the same name already exists for the tenant
        tenant = self.context.get('tenant')  # get tenant from context
        name = data.get('name')
        if name and Location.objects.filter(name=name, tenant=tenant).exists():
            raise serializers.ValidationError(_("Location with this name already exists for this tenant."))
        #check if the contact number starts with a +254
        contact_number = data.get('contact_number')
        if contact_number and not contact_number.startswith("+254"):
            raise serializers.ValidationError(_("Contact number must start with +254."))
        # check if locaction should not have the same address
        address = data.get('address')
        if address and Location.objects.filter(address=address, tenant=tenant).exists():
            raise serializers.ValidationError(_("Location with this address already exists for this tenant."))
        
        return data

    def create(self, validated_data):
        """
        Create a new location instance.
        """
        
        tenant = validated_data.pop('tenant')
        location = Location.objects.create(tenant=tenant, **validated_data)
        
        return location

#serializer to handle location update based on tenant
class LocationUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating an existing location.
    """
    name = serializers.CharField(max_length=255, required=False, allow_blank=True, help_text=_("Name of the location"))
    address = serializers.CharField(max_length=255, required=False, allow_blank=True, help_text=_("Address of the location"))
    latitude = serializers.FloatField(required=False, allow_null=True, help_text=_("Latitude of the location"))
    longitude = serializers.FloatField(required=False, allow_null=True, help_text=_("Longitude of the location"))
    contact_number = serializers.CharField(max_length=20, required=False, allow_blank=True, help_text=_("Contact number of the location"))
    email = serializers.EmailField(required=False, allow_blank=True, help_text=_("Email address of the location"))

    class Meta:
        model = Location
        fields = ["name", "address", "latitude", "longitude", "contact_number", "email"]
        read_only_fields = ["tenant", "created_at", "updated_at"]

    def validate(self, data):
        """ Validate the data before updating an existing location.
        """
        instance = self.instance
        if not instance:
            raise serializers.ValidationError(_("Location does not exist."))
        if 'name' in data and Location.objects.filter(name=data['name'], tenant=instance.tenant).exclude(id=instance.id).exists():
            raise serializers.ValidationError(_("Location with this name already exists for this tenant."))
        return data
    def update(self, instance, validated_data):
        """ Update an existing location instance.
        """
        instance.name = validated_data.get('name', instance.name)
        instance.address = validated_data.get('address', instance.address)
        instance.latitude = validated_data.get('latitude', instance.latitude)
        instance.longitude = validated_data.get('longitude', instance.longitude)
        instance.contact_number = validated_data.get('contact_number', instance.contact_number)
        instance.email = validated_data.get('email', instance.email)
        
        instance.save()
        
        return instance
    
    
#serializer to handle car wash services
class ServiceSerializer(serializers.ModelSerializer):
    """
    Serializer for car wash services.
    """
    name = serializers.CharField(max_length=255, required=True, help_text=_("Name of the service"))
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=True, allow_null=True, help_text=_("Price of the service"))
    description = serializers.CharField(required=False, allow_blank=True, help_text=_("Description of the service"))

    class Meta:
        model = Service
        fields = ["name", "price", "description"]
        read_only_fields = ["id"]

    def validate(self, data):
        """ Validate the data before creating a new service.
        """
        tenant= self.context.get('tenant')  # get tenant from context
        name = data.get('name')
        if Service.objects.filter(name=name, tenant=tenant).exists():
            raise serializers.ValidationError(_("Service with this name already exists."))
        return data
    def create(self, validated_data):
        """ Create a new service instance.
        """
        service = Service.objects.create(**validated_data)
        return service
  
    
    #class serializer to handle service update
    
class ServiceUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating an existing service.
    """
    name = serializers.CharField(max_length=255, required=False, allow_blank=True, help_text=_("Name of the service"))
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True, help_text=_("Price of the service"))
    description = serializers.CharField(required=False, allow_blank=True, help_text=_("Description of the service"))

    class Meta:
        model = Service
        fields = ["name", "price", "description"]
        read_only_fields = ["id"]

    def validate(self, data):
        """ Validate the data before updating an existing service.
        """
        instance = self.instance
        #check if the instance exists
        if not instance:
            raise serializers.ValidationError(_("Service does not exist."))
#check if the name is being updated and if it already exists and but does not belong to the current instance
        name = data.get('name')
        if Service.objects.filter(name=name).exclude(id=instance.pk).exists():
        
            raise serializers.ValidationError(_("Service with this name already exists."))
        return data

    def update(self, instance, validated_data):
        """ Update an existing service instance.
        """
        instance.name = validated_data.get('name', instance.name)
        instance.price = validated_data.get('price', instance.price)
        instance.description = validated_data.get('description', instance.description)
        
        instance.save()
        
        return instance


# class serializer to handle creation of location service
class LocationServiceSerializer(serializers.ModelSerializer):
    """to handle the creation of a location service package."""
    
    location_name = serializers.CharField(source='location.name', read_only=True, help_text=_("Name of the location"))
    service_names = serializers.SerializerMethodField()
    service = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(),
        many=True,
        help_text=_("List of services offered at the location")
    )
    
    service_details= ServiceSerializer(
        source='service',
        many=True,
        read_only=True
    )
    name= serializers.CharField(max_length=255, required=True, help_text=_("Name of the service package"))
    duration = serializers.DurationField(help_text=_("Duration of the service package in minutes"))
    description = serializers.CharField(required=False, allow_blank=True, help_text=_("Description of the service package"))
    
    price = serializers.SerializerMethodField(help_text=_("Total price of the package based on the services included"), read_only=True)

    class Meta:
        model = LocationService
        fields = ['id',"location_name",'service', "name", "duration", "description", "price", 'service_names', 'service_details']
        read_only_fields = ["id",'created_at', "updated_at", "tenant", "location"]
        
    #override the __init__ method to set query set for the service field only to the services that belong to the tenant
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            # Get the tenant from the authenticated user
            tenant = request.user
            self.fields['service'].queryset = Service.objects.filter(tenant=tenant)
        else:
            self.fields['service'].queryset = Service.objects.none()    

    def get_service_names(self, obj):
        """Get the names of the services offered at the location."""
        return [service.name for service in obj.service.all()]
    def get_price(self, obj):
        return obj.price if obj.price is not None else 0.00
    
    def validate(self, data):
        """Validate the data before creating a new location service package."""
        request = self.context.get('request')  # get request from context
        tenant = request.user if request.user.is_authenticated else None
        location = Location.objects.filter(tenant=tenant).first()
        if not location or not isinstance(location, Location):
            raise serializers.ValidationError(_("Valid location is required."))
        
        name =data.get('name',None)
        if not name or not name.strip():
            raise serializers.ValidationError(_("Name is required."))
        if LocationService.objects.filter(name=name, location__tenant=tenant).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError(_("Location service with this name already exists for this location."))
        #validation of services belonging to the tenant
        services = data.get('service', [])
        for service in services:
            if service.tenant != tenant:
                raise serializers.ValidationError(_("Service with ID {} does not belong to the tenant.").format(service.id))
        
        return data

    def create(self, validated_data):
        """Create a new location service package instance."""
        service = validated_data.pop('service')
        location_service = LocationService.objects.create(**validated_data)
        location_service.service.set(service)
        return location_service
    
    def update(self, instance, validated_data):
        """Update an existing location service package instance."""
        instance.name = validated_data.get('name', instance.name)
        instance.duration = validated_data.get('duration', instance.duration)
        instance.description = validated_data.get('description', instance.description)
       
        
        if 'service' in validated_data:
            services = validated_data.pop('service')
            instance.service.set(services)
        
        instance.save()
        
        return instance
