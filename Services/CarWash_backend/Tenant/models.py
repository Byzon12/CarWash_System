from django.contrib.auth.hashers import make_password
from django.db import models
from test.test_reprlib import r
from Users.models import User
from django.utils import timezone
from django.utils.safestring import mark_safe
from Users import models as Users
from django.core.exceptions import ValidationError



# Create your models here.
class Tenant(models.Model):
    #tenant is not associated with a user, it is a separate entity
    """Model representing a tenant in the system.
    A tenant can be a business or organization that uses the application."""
    user = models.OneToOneField(User, on_delete=models.SET_NULL, related_name='tenant_profile', null=True, blank=True)
    name = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=128, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    contact_email = models.EmailField(max_length=254, unique=True)
    contact_phone = models.CharField(max_length=15, blank=True, null=True)
   
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_authenticated(self):
        """Check if the tenant is authenticated."""
        return True
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
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='profiles', null=True, blank=True)
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
        return "No Image"

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

    #model to hanldle Task creation and assignmening task
class Task(models.Model):
    # status choices
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    assigned_to = models.ForeignKey('Staff.StaffProfile', on_delete=models.SET_NULL, related_name='tasks', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    due_date = models.DateTimeField(blank=True, null=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    #override clean function to ensure due_date is not in the past
    def clean(self):
        """
        handle custom validation for Task model.
        This method checks if the due date is in the past and if the assigned staff belongs to
        the same tenant as the task.
        Raises ValidationError if any validation fails.
        :raises ValidationError: If due date is in the past or assigned staff does not belong to the same tenant.
        """
        
        super().clean()
        if self.due_date and self.due_date < timezone.now():
            raise ValidationError("Due date cannot be in the past.")
        
        if self.assigned_to and self.assigned_to.tenant != self.tenant:
            raise ValidationError("Assigned staff must belong to the same tenant.")
        
        def save(self, *args, **kwargs):
            """
            Override save method to ensure clean method is called before saving.
            """
            self.clean()
            super().save(*args, **kwargs)
    def __str__(self):
        return f"Task: {self.title} (Status: {self.status})"
    
    
    class Meta:
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'
        ordering = ['-created_at']
        
        
