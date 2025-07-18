from operator import is_
from tabnanny import verbose
from venv import create
from django.db import models
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.apps import apps
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal

# Model class for staff
from Tenant.models import Tenant

class Staff(models.Model):
    """Model representing a staff member."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='staff_profiles', null=True, blank=True)
    location = models.ForeignKey('Location.Location', on_delete=models.SET_NULL, null=True, blank=True)
    role = models.ForeignKey('StaffRole', on_delete=models.SET_NULL, null=True, blank=False, related_name='staff_role')
    email = models.EmailField(max_length=254, unique=True)
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    password = models.CharField(max_length=128, blank=False, null=True)
    is_active = models.BooleanField(default=True, help_text="Indicates if the staff member is active.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def is_authenticated(self):
        """Check if the staff member is authenticated."""
        return True
    
    @property
    def full_name(self):
        """Get staff full name from profile."""
        try:
            profile = self.staff_profile.first()
            return f"{profile.first_name} {profile.last_name}".strip() if profile else self.username
        except:
            return self.username or self.email
        
    def save(self, *args, **kwargs):
        """Override the save method to hash the password before saving."""
        if self.password and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)
        
    def clean(self):
        """Ensure that the location is set to the employee's tenant location."""
        if self.location and self.tenant:
            if self.location.tenant != self.tenant:
                raise ValidationError("Location must belong to the same tenant as the staff member.")

    def __str__(self):
        return self.email

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
    
    id = models.AutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='staff_roles', null=True, blank=True)
    location = models.ForeignKey('Location.Location', on_delete=models.SET_NULL, related_name='staff_role_location', null=True, blank=True)
    role_type = models.CharField(max_length=50, choices=ROLE_CHOICES, default='staff')
    description = models.TextField(blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    created_at = models.DateField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateField(auto_now=True, null=True, blank=True)
  
    def save(self, *args, **kwargs):
        """Override save method to set the salary based on role type."""
        if not self.salary:
            self.salary = self.SALARY_MAP.get(self.role_type, 0.00)
        super().save(*args, **kwargs)
    
    def clean(self):
        """Ensure that the role type is valid and the location belongs to the tenant."""
        if self.role_type not in dict(self.ROLE_CHOICES):
            raise ValidationError(f"Invalid role type: {self.role_type}.")
        
        if self.location and self.tenant:
            if self.location.tenant != self.tenant:
                raise ValidationError("Location must belong to the same tenant as the staff role.")

    def __str__(self):
        return f"{self.role_type}"

class StaffProfile(models.Model):
    """Model representing a staff profile."""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='staff_profile', null=True, blank=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    location = models.ForeignKey('Location.Location', on_delete=models.SET_NULL, related_name='staff_location', null=True, blank=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    work_email = models.EmailField(max_length=254, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    role = models.ForeignKey(StaffRole, on_delete=models.SET_NULL, null=True, blank=False)
    email = models.EmailField(max_length=254, blank=True, null=True)
    is_active = models.BooleanField(default=True, help_text="Indicates if the staff profile is active.")
    
    @property
    def full_name(self):
        """Get full name of staff member."""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def salary_formatted(self):
        """Get formatted salary."""
        if self.role and self.role.salary:
            return f"KSh {self.role.salary:,.2f}"
        return "KSh 0.00"
    
    def __str__(self):
        return f"{self.full_name} ({self.username})"

# New Model for Walk-in Customers with automatic task creation
class WalkInCustomer(models.Model):
    """Model for managing walk-in customers who don't have bookings."""
    CUSTOMER_STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('in_service', 'In Service'),
        ('completed', 'Completed'),
        ('left', 'Left'),
    ]
    
    # Basic customer info
    name = models.CharField(max_length=200, help_text="Customer's name")
    phone_number = models.CharField(max_length=20, blank=True, null=True, help_text="Customer's phone number")
    email = models.EmailField(blank=True, null=True, help_text="Customer's email")
    vehicle_plate = models.CharField(max_length=20, help_text="Vehicle plate number")
    vehicle_model = models.CharField(max_length=100, blank=True, null=True, help_text="Vehicle model")
    
    # Service details
    location = models.ForeignKey('Location.Location', on_delete=models.CASCADE, related_name='walkin_customers')
    location_service = models.ForeignKey('Location.LocationService', on_delete=models.CASCADE, related_name='walkin_customers')
    assigned_staff = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='walkin_assignments')
    
    # Status and timing
    status = models.CharField(max_length=20, choices=CUSTOMER_STATUS_CHOICES, default='waiting')
    estimated_duration = models.DurationField(null=True, blank=True)
    arrived_at = models.DateTimeField(auto_now_add=True)
    service_started_at = models.DateTimeField(null=True, blank=True)
    service_completed_at = models.DateTimeField(null=True, blank=True)
    
    # Payment
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
    ], default='pending')
    
    # Additional info
    notes = models.TextField(blank=True, null=True, help_text="Additional notes about the customer or service")
    created_by = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, related_name='created_walkins')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def waiting_time(self):
        """Calculate how long customer has been waiting."""
        if self.status == 'waiting' and self.arrived_at:
            return timezone.now() - self.arrived_at
        return None
    
    @property
    def service_duration(self):
        """Calculate service duration if completed."""
        if self.service_started_at and self.service_completed_at:
            return self.service_completed_at - self.service_started_at
        return None
    
    @property
    def total_amount_formatted(self):
        """Get formatted total amount."""
        return f"KSh {self.total_amount:,.2f}" if self.total_amount else "KSh 0.00"
    
    @property
    def primary_task(self):
        """Get the primary task for this customer."""
        return self.tasks.first()
    
    def create_default_task(self):
        """Create a default task for this walk-in customer."""
        if not self.tasks.exists():
            # Import here to avoid circular import
            from .models import WalkInTask
            
            task = WalkInTask.objects.create(
                walkin_customer=self,
                assigned_to=self.assigned_staff,
                created_by=self.created_by,
                task_name=f"{self.location_service.name} - {self.name}",
                description=f"Service: {self.location_service.name} for {self.name} ({self.vehicle_plate})",
                estimated_duration=self.estimated_duration,
                final_price=self.total_amount,
                priority='medium'
            )
            return task
        return self.tasks.first()
    
    def save(self, *args, **kwargs):
        """Override save to create default task automatically."""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Create default task for new customers
        if is_new and self.assigned_staff:
            self.create_default_task()
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Walk-in Customer"
        verbose_name_plural = "Walk-in Customers"
    
    def __str__(self):
        return f"{self.name} - {self.vehicle_plate} ({self.status})"

# Enhanced Task management for walk-in customers
class WalkInTask(models.Model):
    """Tasks specifically for walk-in customers."""
    TASK_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'), 
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Basic task fields
    walkin_customer = models.ForeignKey(WalkInCustomer, on_delete=models.CASCADE, related_name='tasks')
    assigned_to = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='walkin_tasks')
    created_by = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, related_name='created_walkin_tasks')
    task_name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Enhanced timing and tracking
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    paused_at = models.DateTimeField(null=True, blank=True)
    estimated_duration = models.DurationField(null=True, blank=True)
    actual_duration = models.DurationField(null=True, blank=True)
    
    # Task management
    progress_percentage = models.IntegerField(default=0, help_text="Task completion percentage (0-100)")
    requires_approval = models.BooleanField(default=False)
    approved_by = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_walkin_tasks')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Additional tracking
    notes = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True, help_text="Internal staff notes")
    quality_rating = models.IntegerField(null=True, blank=True, help_text="Quality rating 1-5")
    customer_feedback = models.TextField(blank=True, null=True)
    
    # Location and pricing
    final_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def can_start(self):
        """Check if task can be started."""
        return True
    
    @property
    def duration_formatted(self):
        """Get formatted actual duration."""
        if self.actual_duration:
            total_seconds = int(self.actual_duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            if hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        return None
    
    @property
    def estimated_duration_formatted(self):
        """Get formatted estimated duration."""
        if self.estimated_duration:
            total_seconds = int(self.estimated_duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            if hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        return None
    
    @property
    def is_overdue(self):
        """Check if task is overdue based on estimated completion."""
        if self.started_at and self.estimated_duration and self.status not in ['completed', 'cancelled']:
            estimated_completion = self.started_at + self.estimated_duration
            return timezone.now() > estimated_completion
        return False
    
    @property
    def final_price_formatted(self):
        """Get formatted final price."""
        return f"KSh {self.final_price:,.2f}" if self.final_price else "KSh 0.00"
    
    def calculate_actual_duration(self):
        """Calculate and update actual duration."""
        if self.started_at and self.completed_at:
            # Calculate total duration excluding paused time
            total_duration = self.completed_at - self.started_at
            # TODO: Subtract paused duration if tracking pauses
            self.actual_duration = total_duration
            self.save(update_fields=['actual_duration'])
    
    def start_task(self):
        """Start the task if conditions are met."""
        if self.can_start and self.status == 'pending':
            self.status = 'in_progress'
            self.started_at = timezone.now()
            self.save(update_fields=['status', 'started_at'])
            
            # Update customer status if this is the primary task
            if self.walkin_customer.primary_task == self:
                self.walkin_customer.status = 'in_service'
                self.walkin_customer.service_started_at = timezone.now()
                self.walkin_customer.save(update_fields=['status', 'service_started_at'])
            
            return True
        return False
    
    def complete_task(self, final_price=None, quality_rating=None):
        """Complete the task."""
        if self.status == 'in_progress':
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.progress_percentage = 100
            
            if final_price:
                self.final_price = final_price
            if quality_rating:
                self.quality_rating = quality_rating
                
            self.calculate_actual_duration()
            
            # Update customer status if this is the primary task
            if self.walkin_customer.primary_task == self:
                self.walkin_customer.status = 'completed'
                self.walkin_customer.service_completed_at = timezone.now()
                self.walkin_customer.save(update_fields=['status', 'service_completed_at'])
            
            self.save()
            return True
        return False
    
    def pause_task(self):
        """Pause the task."""
        if self.status == 'in_progress':
            self.status = 'paused'
            self.paused_at = timezone.now()
            self.save(update_fields=['status', 'paused_at'])
            return True
        return False
    
    def resume_task(self):
        """Resume a paused task."""
        if self.status == 'paused':
            self.status = 'in_progress'
            self.paused_at = None
            self.save(update_fields=['status', 'paused_at'])
            return True
        return False
    
    def cancel_task(self, reason=None):
        """Cancel the task."""
        if self.status not in ['completed', 'cancelled']:
            self.status = 'cancelled'
            if reason:
                self.internal_notes = f"Cancelled: {reason}"
            self.save(update_fields=['status', 'internal_notes'])
            return True
        return False
    
    def clean(self):
        """Validate the task."""
        super().clean()
        
        # Validate quality rating
        if self.quality_rating is not None and (self.quality_rating < 1 or self.quality_rating > 5):
            raise ValidationError("Quality rating must be between 1 and 5")
        
        # Validate progress percentage
        if self.progress_percentage < 0 or self.progress_percentage > 100:
            raise ValidationError("Progress percentage must be between 0 and 100")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Walk-in Task"
        verbose_name_plural = "Walk-in Tasks"
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['walkin_customer', 'status']),
        ]
    
    def __str__(self):
        return f"{self.task_name} - {self.walkin_customer.name} ({self.status})"

# Task Template for common task types
class WalkInTaskTemplate(models.Model):
    """Template for common walk-in task types."""
    name = models.CharField(max_length=200)
    description = models.TextField()
    estimated_duration = models.DurationField()
    service_items = models.JSONField(default=list, help_text="Standard service items/steps")
    default_price = models.DecimalField(max_digits=10, decimal_places=2)
    requires_approval = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='task_templates')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Task Template"
        verbose_name_plural = "Task Templates"
    
    def __str__(self):
        return self.name

# New Model for Walk-in Customer Payments
class WalkInPayment(models.Model):
    """Model for tracking walk-in customer payments."""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
    ]
    
    # Payment details
    walkin_customer = models.ForeignKey(WalkInCustomer, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # M-Pesa specific fields
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    checkout_request_id = models.CharField(max_length=100, blank=True, null=True)
    merchant_request_id = models.CharField(max_length=100, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Response data
    mpesa_response = models.JSONField(blank=True, null=True, help_text="M-Pesa STK push response")
    mpesa_query_response = models.JSONField(blank=True, null=True, help_text="M-Pesa transaction query response")
    callback_response = models.JSONField(blank=True, null=True, help_text="M-Pesa callback response")
    
    # Additional info
    failure_reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    processed_by = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_payments')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def amount_formatted(self):
        """Get formatted amount."""
        return f"KSh {self.amount:,.2f}"
    
    @property
    def is_successful(self):
        """Check if payment was successful."""
        return self.status == 'completed'
    
    @property
    def is_pending(self):
        """Check if payment is still pending."""
        return self.status in ['pending', 'processing']
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Walk-in Payment"
        verbose_name_plural = "Walk-in Payments"
    
    def __str__(self):
        return f"{self.walkin_customer.name} - {self.amount_formatted} ({self.status})"


