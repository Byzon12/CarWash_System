from venv import create
from django.db import models
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from Tenant.models import Tenant, EmployeeRole
from django.contrib.auth.models import User


# Model class for staff profile

    #
class StaffRole(models.Model):
 
    ROLE_CHOICES = [
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('cleaner', 'Cleaner'),
        ('security', 'Security'),
        ('receptionist', 'Receptionist'),
      
    ]


    SALARY_MAP = {
        'manager': 5000.00,
        'staff': 3000.00,
        'cleaner': 2000.00,
        'security': 2500.00,
        'receptionist': 3500.00,
    }
    
    """Model representing different roles an employee can have within a tenant."""
    role_type = models.CharField(max_length=50, choices=ROLE_CHOICES, default='staff')
    description = models.TextField(blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
  
    def save(self, *args, **kwargs):
        """Override save method to set the salary based on role type."""
        if not self.salary:
            self.salary = self.SALARY_MAP.get(self.role_type, 0.00)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.role_type} "
    

class StaffProfile(models.Model):
   
    user = models.OneToOneField(User, on_delete=models.SET_NULL, related_name='staff_profile', null=True, blank=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='staff_profiles', null=True, blank=True)
    location = models.ForeignKey('Location.Location', on_delete=models.SET_NULL, related_name='staff_location', null=True, blank=True)
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    work_email= models.EmailField(max_length=254, unique=True)
    full_name = models.CharField(max_length=100)
    password = models.CharField(max_length=128, blank=False, null=True)
    role = models.ForeignKey(StaffRole, on_delete=models.SET_NULL, null=True, blank=False, related_name='staff_role')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(max_length=254, blank=True, null=True)
    
    
    # clean method to ensure location is set to the employee's tenant location
    def clean(self):
        #ensure that the location belongs to the same tenanta as the employee
        if self.location and self.tenant:
            if self.location.tenant != self.tenant:
                raise ValueError("Location must belong to the same tenant as the employee.")
    
    def save(self, *args, **kwargs):
        """
        Override the save method to hash the password before saving.
        """
        if self.password:
            self.password = make_password(self.password)
        super().save(*args, **kwargs)
    
    def __str__(self):
        """
        String representation of the StaffProfile model.
        """
        return f"{self.full_name} ({self.username}) - {self.tenant.name if self.tenant else 'No Tenant'}"
    
    
    #car checkin item list
class CarCheckInItem(models.Model):
    """
    Model representing a car check-in item.
    This model is used to track items associated with a car during check-in.
    """
    task= models.ForeignKey('Task', on_delete=models.CASCADE, related_name='checkin_items')
    item_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

 