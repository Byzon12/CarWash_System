from django.db import models
from Users.models import User
from django.utils import timezone


# Create your models here.
class Tenant(models.Model):
    #tenant is not associated with a user, it is a separate entity
    """Model representing a tenant in the system.
    A tenant can be a business or organization that uses the application."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    contact_email = models.EmailField(max_length=254, unique=True)
    contact_phone = models.CharField(max_length=15, blank=True, null=True)
   
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Tenant'
        verbose_name_plural = 'Tenants'
        ordering = ['name']
#creating tenant profile model
class TenantProfile(models.Model):
    tenant= models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='profiles', null=True, blank=True)
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    business_name = models.CharField(max_length=100, blank=True, null=True)
    business_email = models.EmailField(max_length=254, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    logo = models.ImageField(upload_to='tenant_logos/', blank=True, null=True)
   
    def save(self, *args, **kwargs):
        """Override save method to set the tenant if not already set."""
        if not self.tenant:
            # Automatically assign the first tenant if no tenant is set
            self.tenant = Tenant.objects.first()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.business_name} Profile"

    class Meta:
        verbose_name = 'Tenant Profile'
        verbose_name_plural = 'Tenant Profiles'
        
    #comment
    #