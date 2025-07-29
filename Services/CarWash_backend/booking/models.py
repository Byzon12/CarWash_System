from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from Tenant.models import TenantProfile, Tenant
from Location.models import Location, LocationService, Service
from Users.models import CustomerProfile
import uuid
from datetime import timedelta
from django.utils import timezone



class booking(models.Model):
    """
    Enhanced Model representing a customer booking for a car wash location and service.
    This model includes comprehensive fields for managing bookings, including customer details,
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Payment'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('paypal', 'PayPal'),
        ('visa', 'Visa'),
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ]

  

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('expired', 'Expired'),
    ]

    # main booking fields
    id = models.AutoField(primary_key=True, help_text="Unique identifier for the booking.")
    booking_number = models.CharField(max_length=20, unique=True, editable=False, help_text="Human-readable booking reference", blank=True, null=True)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='bookings', help_text="The car wash location where the booking is made.")
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='bookings', help_text="The customer making the booking.")
    location_service = models.ForeignKey(LocationService, on_delete=models.CASCADE, related_name='bookings', help_text="The specific service package booked at this location.")
    
    # Booking timing
    booking_date = models.DateTimeField(help_text="The start time of the booking.")
    time_slot_end = models.DateTimeField(blank=True, null=True, help_text="The calculated end time of the booking based on service duration.")
    
    
    # Customer details for this booking
    customer_name = models.CharField(max_length=100, help_text="Customer name for this booking", blank=True, null=True)
    customer_phone = models.CharField(max_length=15, help_text="Customer phone number", blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True, help_text="Customer email address", default=None)
    vehicle_details = models.TextField(blank=True, null=True, help_text="Vehicle make, model, color, etc.")
    special_instructions = models.TextField(blank=True, null=True, help_text="Special customer instructions")
    
    # Pricing
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total amount to be paid", default=0)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Payment tracking
    payment_reference = models.CharField(max_length=100, null=True, blank=True, help_text="Payment gateway reference")
    mpesa_checkout_request_id = models.CharField(max_length=100, null=True, blank=True, help_text="M-Pesa checkout request ID")
    mpesa_transaction_id = models.CharField(max_length=100, null=True, blank=True, help_text="M-Pesa transaction ID")
    
    # Additional flags
    is_prepaid = models.BooleanField(default=False, help_text="Indicates if the payment was made upfront.")
    requires_confirmation = models.BooleanField(default=True, help_text="Whether booking needs staff confirmation")
    send_reminders = models.BooleanField(default=True, help_text="Whether to send booking reminders")
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True, help_text="When the booking was confirmed")
    payment_completed_at = models.DateTimeField(null=True, blank=True, help_text="When payment was completed")

    class Meta:
        verbose_name = "booking"
        verbose_name_plural = "bookings"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['booking_date']),
            models.Index(fields=['customer']),
            models.Index(fields=['location']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['mpesa_checkout_request_id']),
        ]

    def save(self, *args, **kwargs):
        # Generate booking number if not exists
        if not self.booking_number:
            self.booking_number = self.generate_booking_number()
        
        # Calculate end time if not set
        if not self.time_slot_end and self.booking_date and self.location_service:
            self.time_slot_end = self.booking_date + self.location_service.duration
        
        # Calculate total amount
        self.total_amount = self.location_service.price if self.location_service else 0
        
        # Set payment completed timestamp
        if self.payment_status == 'paid' and not self.payment_completed_at:
            self.payment_completed_at = timezone.now()
        
        # Set confirmed timestamp
        if self.status == 'confirmed' and not self.confirmed_at:
            self.confirmed_at = timezone.now()
        
        super().save(*args, **kwargs)

    def generate_booking_number(self):
        """Generate a unique booking number"""
        import random
        import string
        prefix = "BK"
        timestamp = timezone.now().strftime("%Y%m%d")
        random_suffix = ''.join(random.choices(string.digits, k=4))
        return f"{prefix}{timestamp}{random_suffix}"

    def clean(self):
        """Custom validation"""
        super().clean()
        
        # Validate booking date is in the future
        if self.booking_date and self.booking_date <= timezone.now():
            raise ValidationError("Booking date must be in the future.")
        
        # Validate location service belongs to location
        if self.location_service and self.location and self.location_service.location != self.location:
            raise ValidationError("Selected service does not belong to the specified location.")
        
        # Validate phone number format for M-Pesa if the payment method is M-Pesa
        if self.payment_method == 'mpesa' and self.customer_phone:
            if not self.is_valid_kenyan_phone(self.customer_phone):
                raise ValidationError("Invalid Kenyan phone number format for M-Pesa payments.")

    def is_valid_kenyan_phone(sef, phone):
        """Validate Kenyan phone number format"""
        import re
        phone = re.sub(r'\D', '', phone)
        return (
            (phone.startswith('254') and len(phone) == 12) or
            (phone.startswith('7') and len(phone) == 9) or
            (phone.startswith('0') and len(phone) == 10)
        )

    def can_be_cancelled(self):
        """Check if booking can be cancelled"""
        if self.status in ['completed', 'cancelled']:
            return False
        # Allow cancellation up to 2 hours before booking
        return self.booking_date > timezone.now() + timedelta(hours=2)

    def can_be_modified(self):
        """Check if booking can be modified"""
        if self.status in ['completed', 'cancelled']:
            return False
        # Allow modification up to 4 hours before booking
        return self.booking_date > timezone.now() + timedelta(hours=4)

    def is_overdue(self):
        """Check if booking is overdue"""
        return self.booking_date < timezone.now() and self.status not in ['completed', 'cancelled']

    def __str__(self):
        return f"{self.booking_number} - {self.customer_name} at {self.location.name} on {self.booking_date.strftime('%Y-%m-%d %H:%M')}"

class BookingStatusHistory(models.Model):
    """Track booking status changes"""
    booking = models.ForeignKey(booking, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=20, blank=True, null=True)
    to_status = models.CharField(max_length=20)
    reason = models.TextField(blank=True, null=True)
    changed_by = models.CharField(max_length=100, blank=True, null=True)  # Could be system or user
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

class PaymentTransaction(models.Model):
    """Track payment transactions"""
    TRANSACTION_STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
    ('mpesa', 'M-Pesa'),
    ('paypal', 'PayPal'),
    ('visa', 'Visa'),
    ('cash', 'Cash'),
    ('bank_transfer', 'Bank Transfer'),
    ]

    booking = models.ForeignKey(booking, on_delete=models.CASCADE, related_name='payment_transactions')
    transaction_id = models.CharField(max_length=100, unique=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS_CHOICES, default='initiated')
    
    # Gateway specific fields
    gateway_reference = models.CharField(max_length=100, blank=True, null=True)
    gateway_response = models.JSONField(blank=True, null=True)
    
    # M-Pesa specific fields
    mpesa_receipt_number = models.CharField(max_length=100, blank=True, null=True)
    mpesa_phone_number = models.CharField(max_length=15, blank=True, null=True)
    
    # Timestamps
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-initiated_at']

    def __str__(self):
        return f"{self.transaction_id} - {self.payment_method} - {self.amount}"