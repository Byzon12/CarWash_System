

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from Tenant.models import Employee, TenantProfile, Tenant, EmployeeRole
from django.contrib.auth.hashers import check_password
from Location.models import Location, Service, LocationService

#serializer to handle location creation based on tenant
class LocationSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new location.
    """
    tenant = serializers.PrimaryKeyRelatedField(queryset=Tenant.objects.all(), write_only=True, required=True)
    name = serializers.CharField(max_length=255, required=True, help_text=_("Name of the location"))
    address = serializers.CharField(max_length=255, required=True, help_text=_("Address of the location"))
    latitude = serializers.FloatField(required=True, help_text=_("Latitude of the location"))
    longitude = serializers.FloatField(required=True, help_text=_("Longitude of the location"))
    contact_number = serializers.CharField(max_length=20, required=False, allow_blank=True, help_text=_("Contact number of the location"))
    email = serializers.EmailField(required=False, allow_blank=True, help_text=_("Email address of the location"))
    
    class Meta:
        model = Location
        fields = ["tenant", "name", "address", "latitude", "longitude", "contact_number", "email"]
        read_only_fields = ["created_at", "updated_at"]
        
    #method to check if there is a another name the same to this
    
    

    def validate(self, data):
        """ Validate the data before creating a new location.
        """
        tenant = data.get('tenant', None)
        name = data.get('name', None)
        if not tenant:
            raise serializers.ValidationError(_("Tenant is required to create a location."))
        if not Tenant.objects.filter(id=tenant.id).exists():
            raise serializers.ValidationError(_("Tenant does not exist."))
        if name and Location.objects.filter(name=name, tenant=tenant).exists():
            raise serializers.ValidationError(_("Location with this name already exists for this tenant."))
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
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True, help_text=_("Price of the service"))
    description = serializers.CharField(required=False, allow_blank=True, help_text=_("Description of the service"))

    class Meta:
        model = Service
        fields = ["name", "price", "description"]
        read_only_fields = ["id"]

    def validate(self, data):
        """ Validate the data before creating a new service.
        """
        if Service.objects.filter(name=data.get('name')).exists():
            raise serializers.ValidationError(_("Service with this name already exists."))
        return data
    def create(self, validated_data):
        """ Create a new service instance.
        """
        service = Service.objects.create(**validated_data)
        return service