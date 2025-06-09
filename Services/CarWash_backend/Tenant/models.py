from django.contrib.auth.hashers import make_password
from django.db import models
from Users.models import User
from django.utils import timezone
from django.utils.safestring import mark_safe



# Create your models here.
class Tenant(models.Model):
    #tenant is not associated with a user, it is a separate entity
    """Model representing a tenant in the system.
    A tenant can be a business or organization that uses the application."""
    name = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=128, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    contact_email = models.EmailField(max_length=254, unique=True)
    contact_phone = models.CharField(max_length=15, blank=True, null=True)
   
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
     #hash password before saving
    def save(self, *args, **kwargs):
        if self.password:
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

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
    
    def image_tag(self):
        if self.logo:
            return mark_safe(f'<img src="{self.logo.url}" width="50" height="50" />')
        return "No Logo"
        return "No Logo"
   
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
class EmployeeRole(models.Model):
 
    ROLE_CHOICES = [
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('cleaner', 'Cleaner'),
        ('driver', 'Driver'),
        ('receptionist', 'Receptionist'),
    ]
    """Model representing different roles an employee can have within a tenant."""
    role_type = models.CharField(max_length=50, choices=ROLE_CHOICES, default='staff')
    description = models.TextField(blank=True, null=True)
    salary_role = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.role_type}"
 #clf.role_type}" 
    
# creating employee model for tenant
class Employee(models.Model):

    
    """Model representing an employee of a tenant.
    An employee is associated with only one tenant and has their own portal profile."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='employees')
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    work_email= models.EmailField(max_length=254, unique=True)
    full_name = models.CharField(max_length=100)
    position = models.CharField(max_length=100, blank=True, null=True, )
    role = models.ForeignKey(EmployeeRole, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(max_length=254, blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} - {self.position} at {self.tenant.name}"
