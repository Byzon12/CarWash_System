from django.db import models

from Tenant.models import Tenant

# Create your models here.
 
 #model for Location
class Location(models.Model):
    """
    Model representing a car wash location.
    """
    id= models.AutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='locations')
    name = models.CharField(max_length=255, unique=True)
    address = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "Locations"
        ordering = ['name']

#model for Carwash services
class Service(models.Model):
    """
    Model representing a car wash service.
    """
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Service"
        verbose_name_plural = "Services"
        ordering = ['name']
        
#model class for car wash service parkage

class LocationService(models.Model):
    """
    Model representing a car wash service package.
    """
   
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='location_services')
    service = models.ManyToManyField(Service,related_name='location_services')
    name = models.CharField(max_length=255)
    duration = models.DurationField(help_text="Duration of the package in hours and minutes")
    description = models.TextField(blank=True, null=True, help_text="Description of the package")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Location Service"
        verbose_name_plural = "Location Services"
        ordering = ['name']