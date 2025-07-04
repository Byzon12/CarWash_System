from venv import create
from django.db import models
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.apps import apps
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

#model class for staff
from Tenant.models import Tenant
class Staff(models.Model):
    """Model representing a staff member."""
   # user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='staff_profiles', null=True, blank=True)
    location = models.ForeignKey('Location.Location', on_delete=models.SET_NULL, null=True, blank=True)
    role= models.ForeignKey('StaffRole', on_delete=models.SET_NULL, null=True, blank=False, related_name='staff_role')
    email = models.EmailField(max_length=254, unique=True)
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    password = models.CharField(max_length=128, blank=False, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def is_authenticated(self):
        """
        Check if the staff member is authenticated.
        This method returns True for all staff members.
        """
        return True
    
        
    def save(self, *args, **kwargs):
        """
        Override the save method to hash the password before saving.
        """
        if self.password:
            self.password = make_password(self.password)
        super().save(*args, **kwargs)
        
    # ensures that location set belong to this tenant
    def clean(self):
        """
        Ensure that the location is set to the employee's tenant location.
        """
        if self.location and self.tenant:
            if self.location.tenant != self.tenant:
                raise ValidationError("Location must belong to the same tenant as the staff member.")
    

    def __str__(self):
        return self.email


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
    id = models.AutoField(primary_key=True)
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
   
    """Model representing a staff profile.
    This model is used to store staff information, including their user account
    and role within a tenant.
    """
    
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='staff_profile', null=True, blank=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    location = models.ForeignKey('Location.Location', on_delete=models.SET_NULL, related_name='staff_location', null=True, blank=True)
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    work_email= models.EmailField(max_length=254, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    role = models.ForeignKey(StaffRole, on_delete=models.SET_NULL, null=True, blank=False)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(max_length=254, blank=True, null=True)
    
    #property dicorator to authenitcate the staff profile
     # Make it behave like an authenticated user
    

    # (Optional, for DRF compatibility)
   
    
    
    # clean method to ensure location is set to the employee's tenant location

    
    def __str__(self):
        """
        String representation of the StaffProfile model.
        """
        return f"({self.username})"
    
    
    #car checkin item list


 