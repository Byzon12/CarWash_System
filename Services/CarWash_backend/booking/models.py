from django.db import models
from Tenant.models import TenantProfile, Tenant, Employee
from Location.models import Location, LocationService, Service
from Users.models import CustomerProfile


# Create your models here.

class Booking(models.Model):
    """
    Model representing a customer booking for a car wash service at a specific location.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('paypal', 'PayPal'),
        ('visa', 'Visa'),
        ('cash', 'Cash'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'), 
    ]

    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='bookings', help_text="The car wash location where the booking is made.")
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='bookings', help_text="The customer making the booking.")
    location_service = models.ForeignKey(LocationService, on_delete=models.CASCADE, related_name='bookings', help_text="The specific service package booked at this location.")
   # staff_member = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_bookings', help_text="The staff member assigned to this booking (optional).")
    booking_date = models.DateTimeField(help_text="The start time of the booking.")
    time_slot_end = models.DateTimeField(blank=True, null=True, help_text="The calculated end time of the booking based on service duration.")
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="The total amount for the booking.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_reference = models.CharField(max_length=100, null=True, blank=True, unique=True) # Reference should be unique
    is_prepaid = models.BooleanField(default=False, help_text="Indicates if the payment was made upfront.")
    created_at = models.DateTimeField(auto_now_add=True)
    
    updated_at = models.DateTimeField(auto_now=True) # Added for tracking changes

    class Meta:
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"
        ordering = ['booking_date']
        
    #function to calculate the end time of the booking based on the service duration
    def save(self, *args, **kwargs):
        if not self.time_slot_end:
            # Calculate end time based on the service duration
            self.time_slot_end = self.booking_date + self.location_service.duration
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking for {self.customer} at {self.location.name} for {self.location_service.name} on {self.booking_date.strftime('%Y-%m-%d %H:%M')} - Status: {self.status}"