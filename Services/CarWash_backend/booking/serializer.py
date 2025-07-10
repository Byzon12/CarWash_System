from ctypes import FormatError
from email import message
from os import read, write
from pydoc import locate
from urllib import request
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db.models import Q
from django.utils import timezone
from django.db import transaction
from Users.serializer import CustomerProfileSerializer
from Location.serializer import LocationServiceSerializer, LocationSerializer


from .models import CustomerProfile
from .models import Location, LocationService, booking

# Import models
from booking.models import booking

class BookingSerializer(serializers.ModelSerializer):
    """
    Serializer for the Booking model.
    """
    class Meta:
        model = booking
        fields = '__all__'
        read_only_fields = [
            'customer', 
            'location', 
            'location_service', 
            'status', 
            'payment_status', 
            'payment_reference', 
            'created_at', 
            'updated_at'
        ]

# serializer class to create a booking
class BookingCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a booking.
    Handles all booking fields with proper validation and automatic field population.
    """
    # Required fields for booking creation, write-only fields will be auto-populated
    location = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(),
        write_only=True,
        help_text=_("The car wash location where the booking is made.")
    )
    location_service = serializers.PrimaryKeyRelatedField(
        queryset=LocationService.objects.all(),
        write_only=True,
        help_text=_("The specific service package booked at this location.")
    )
    booking_date = serializers.DateTimeField(
        write_only=True,
        help_text=_("The start date and time of the booking.")
    )
    
    # Optional customer details (can override profile defaults)

    customer_phone = serializers.CharField(
        max_length=15, 
        required=False, 
        allow_blank=True,
        help_text=_("Customer phone number (required for M-Pesa payments)")
    )
   
    vehicle_details = serializers.CharField(
        required=False, 
        allow_blank=True,
        help_text=_("Vehicle make, model, color, license plate, etc.")
    )
    special_instructions = serializers.CharField(
        required=False, 
        allow_blank=True,
        help_text=_("Special instructions for the service")
    )
    
    # Payment preferences
    payment_method = serializers.ChoiceField(
        choices=booking.PAYMENT_METHOD_CHOICES,
        required=False,
        help_text=_("Preferred payment method")
    )
    
    # Optional flags
    requires_confirmation = serializers.BooleanField(
        default=True,
        help_text=_("Whether booking needs staff confirmation")
    )
    send_reminders = serializers.BooleanField(
        default=True,
        help_text=_("Whether to send booking reminders")
    )
    
    # Read-only fields (auto-populated)
    customer_email = serializers.EmailField(read_only=True,
        source='customer.email',
        help_text=_("Customer email from profile (read-only)"))
    customer_name = serializers.PrimaryKeyRelatedField(
        source='customer.first_name', 
        read_only=True, 
        help_text=_("Customer name from profile")
    )
    customer = serializers.PrimaryKeyRelatedField(read_only=True,
        help_text=_("Customer ID from profile (read-only)"))
    booking_number = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    payment_status = serializers.CharField(read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    time_slot_end = serializers.DateTimeField(read_only=True)

    class Meta:
        model = booking
        fields = [
            # Core booking fields
            'location',
            'location_service', 
            'booking_date',
            
            # Customer details
            
            'customer_phone',
           
            'vehicle_details',
            'special_instructions',
            
            # Payment and preferences
            'payment_method',
            'requires_confirmation',
            'send_reminders',
            
            # Read-only fields
            'customer',
            'booking_number',
            'status',
            'customer_name',
            'customer_email',
            'payment_status',
            'total_amount',
            'time_slot_end',
            'created_at',
        ]
        read_only_fields = [
            'customer',
            'booking_number', 
            'status', 
            'customer_name',
            'customer_email',
            'payment_status',
            'total_amount',
            'time_slot_end',
            'payment_reference',
            'mpesa_checkout_request_id',
            'mpesa_transaction_id',
            'is_prepaid',
            'confirmed_at',
            'payment_completed_at',
            'created_at', 
            'updated_at'
        ]

    def validate_booking_date(self, value):
        """Validate that booking date is in the future"""
        if value <= timezone.now():
            raise serializers.ValidationError(_("Booking date must be in the future."))
        return value
    
    def validate_customer_phone(self, value):
        """Validate phone number format if provided"""
        if value:
            # Validate Kenyan phone number format and it as required for M-Pesa payments
            if not value.startswith(('07', '+254', '254', '01')):
                raise serializers.ValidationError(_("Phone number must start with '07', '+254', '254', or '01'."))
            # Remove non-digit characters and check length
            phone = ''.join(filter(str.isdigit, value))
            if phone.startswith('0'):
                phone = '254' + phone[1:]
            elif phone.startswith('7') and len(phone) == 9:
                phone = '254' + phone
            elif phone.startswith('+254'):
                phone = phone[1:]
            elif not phone.startswith('254') and len(phone) == 9:
                phone = '254' + phone
            # Validate length
            # Phone number should be 12 digits long after formatting
            if not phone.startswith('254') or len(phone) != 12:
                raise serializers.ValidationError(_("Phone number must be 12 digits long after formatting."))
            # Check if phone number length is between 9 and 12 digits
            if len(phone) < 9 or len(phone) > 12:
                raise serializers.ValidationError(_("Invalid phone number format."))
        return value

    def validate(self, data):
        """Object-level validation"""
        location = data.get('location')
        location_service = data.get('location_service')
        booking_date = data.get('booking_date')
        payment_method = data.get('payment_method')
        customer_phone = data.get('customer_phone')

        # Validate location service belongs to location
        if location_service and location and location_service.location != location:
            raise serializers.ValidationError({
                'location_service': _("The selected service does not belong to the specified location.")
            })

        # Check for booking conflicts (same location and overlapping time)
        if location and booking_date and location_service:
            # Calculate end time for conflict checking
            end_time = booking_date + location_service.duration
            
            # Check for overlapping bookings
            conflicting_bookings = booking.objects.filter(
                location=location,
                status__in=['pending', 'confirmed', 'in_progress'],
                booking_date__lt=end_time,
                time_slot_end__gt=booking_date
            )
            
            if conflicting_bookings.exists():
                raise serializers.ValidationError({
                    'booking_date': _("This time slot conflicts with existing bookings.")
                })

        
        if payment_method == 'mpesa':
            if not customer_phone:
                # Try to get phone from user profile
                request = self.context.get('request')
                if request and hasattr(request.user, 'Customer_profile'):
                    profile_phone = getattr(request.user.Customer_profile, 'phone_number', None)
                    if not profile_phone:
                        raise serializers.ValidationError({
                            'customer_phone': _("Phone number is required for M-Pesa payments.")
                        })
                else:
                    raise serializers.ValidationError({
                        'customer_phone': _("Phone number is required for M-Pesa payments.")
                    })

        return data

    def create(self, validated_data):
        """Create a new booking instance with auto-populated fields"""
        request = self.context.get('request')
        
        # Get customer profile
        try:
            customer_profile = request.user.Customer_profile
            validated_data['customer'] = customer_profile
        except AttributeError:
            raise serializers.ValidationError({
                'customer': _("No customer profile associated with this user.")
            })

        # Auto-populate customer details from profile if not provided
        if not validated_data.get('customer_name'):
            validated_data['customer_name'] = f"{customer_profile.first_name} {customer_profile.last_name}".strip()
        
        if not validated_data.get('customer_email'):
            validated_data['customer_email'] = customer_profile.email
        
        if not validated_data.get('customer_phone'):
            validated_data['customer_phone'] = getattr(customer_profile, 'phone_number', '')

        # Set default status
        validated_data['status'] = 'draft'
        validated_data['payment_status'] = 'pending'
        
        # Create the booking (save method will handle total_amount and time_slot_end calculation)
        booking_instance = booking.objects.create(**validated_data)
        
        return booking_instance

    def to_representation(self, instance):
        """Custom representation with additional computed fields"""
        data = super().to_representation(instance)
        
        # Add location and service details
        if instance.location:
            data['location_details'] = {
                'id': instance.location.id,
                'name': instance.location.name,
                'address': instance.location.address,
            }
        
        if instance.location_service:
            data['service_details'] = {
                'id': instance.location_service.id,
                'name': instance.location_service.name,
                'duration': str(instance.location_service.duration),
                'price': instance.location_service.price,
                'description': instance.location_service.description,
            }
        
        # Add duration in minutes for frontend convenience
        if instance.location_service and instance.location_service.duration:
            total_seconds = instance.location_service.duration.total_seconds()
            data['duration_minutes'] = int(total_seconds / 60)
        
        return data
#class serialier to update a booking
class BookingUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating a booking.
    This serializer allows updating the booking date, status, payment status,
    and payment reference. It does not allow changing the customer or location.
    """
    class Meta:
        model = booking
        fields =  ['customer', 'booking_date', 'status', 'payment_status', 'payment_reference', 'location', 'location_service']
        read_only_fields = ['customer', 'location', 'created_at', 'updated_at']

#function to validate the booking date

    def validate_booking_date(self, value):
        """ Validate the booking date to ensure it is in the future.
        """
        if not value:
            raise serializers.ValidationError(_("Booking date is required."))
        if value <= timezone.now():
            raise serializers.ValidationError(_("Booking date must be in the future."))
        return value

    # object lavel to validate the booking
    def validate(self, data):
        """object level validation for the booking. 
            """
        instance = self.instance
        booking_date = data.get('booking_date', instance.booking_date)
        request = self.context.get('request')
        user =getattr(request, 'user', None)
         #prevent updating locationservices that belong to a different location
        if 'location_service' in data:
            location_service = data['location_service']
            if location_service.location != instance.location:
                raise serializers.ValidationError(_("Cannot update location service to a different location."))

        #prevent booking if the status is cancelled or completed
        if instance.status in ['cancelled', 'completed']:
            raise serializers.ValidationError(_("Cannot update a booking that is cancelled or completed."))
        # Check if the booking date conflicts with existing bookings
        existing_bookings = booking.objects.filter(
            location=instance.location,
            booking_date=booking_date,
        ).exclude(id=instance.id)   # Exclude the current booking instance
        if existing_bookings.exists():
            raise serializers.ValidationError(_("Booking date conflicts with existing bookings."))
        # If the booking date is changed, ensure it is in the future
        if booking_date <= timezone.now():
            raise serializers.ValidationError(_("Booking date must be in the future."))
        return data
    
    #
    def update(self, instance, validated_data):
        """Update the booking instance with the validated data."""
        user = self.context.get('request').user
        
        old_data = {
            'location_service': instance.location_service,
            'booking_date': instance.booking_date,
            'status': instance.status,
            'payment_status': instance.payment_status,
            'payment_reference': instance.payment_reference
        }
        with transaction.atomic():
            # Log the old data before updating
            instance.location_service = validated_data.get('location_service', instance.location_service)
            instance.booking_date = validated_data.get('booking_date', instance.booking_date)
            instance.status = validated_data.get('status', instance.status)
            instance.payment_status = validated_data.get('payment_status', instance.payment_status)
            instance.payment_reference = validated_data.get('payment_reference', instance.payment_reference)
            instance.save()
        return instance

#serializer to get the booking details
class BookingDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for retrieving booking details.
    This serializer includes all fields of the Booking model.
    It is used to get the details of a specific booking instance.
    
    """
    customer = CustomerProfileSerializer(read_only=True, help_text=_("The customer making the booking."))
    location = LocationSerializer(read_only=True, help_text=_("The car wash location where the booking is made."))
    location_service = LocationServiceSerializer(read_only=True, help_text=_("The specific service package booked at this location."))
    class Meta:
        model = booking
        fields = '__all__'
        read_only_fields = [
            'customer', 
            'location', 
            'status', 
            'payment_status', 
            'payment_reference', 
            'created_at', 
            'updated_at'
        ]
        
       #claculate the end time of the booking based on the service duration
    def get_time_slot_end(self, obj):
        """
        Calculate the end time of the booking based on the service duration.
        """
        if obj.time_slot_end:
            return obj.time_slot_end
        if obj.booking_date and obj.location_service:
            return obj.booking_date + obj.location_service.duration
        return None
    
    
    #serializer to handle booking cancellation
class BookingCancellationSerializer(serializers.ModelSerializer):
    """
    Serializer for cancelling a booking.
    This serializer allows cancelling a booking by updating its status to 'cancelled'.
    It does not allow changing any other fields.
    """
    class Meta:
        model = booking
        fields = ['status']
        read_only_fields = ['customer', 'location', 'location_service', 'booking_date', 'amount', 'payment_method', 'is_prepaid']

    def validate(self, data):
        """Validate the cancellation request."""
        instance = self.instance
        if instance.status in ['cancelled', 'completed']:
            raise serializers.ValidationError(_("Cannot cancel a booking that is already cancelled or completed."))
        return data

    def update(self, instance, validated_data):
        """Update the booking status to 'cancelled'."""
        instance.status = 'cancelled'
        instance.save()
        return instance

class PaymentInitiationSerializer(serializers.Serializer):
    """
    Serializer for initiating payment for a booking.
    """
    booking_id = serializers.IntegerField(
        help_text=_("The ID of the booking to initiate payment for.")
    )
    payment_method = serializers.ChoiceField(
        choices=[
            ('mpesa', 'M-Pesa'),
            ('paypal', 'PayPal'),
            ('visa', 'Visa/Card'),
            ('cash', 'Cash')
        ],
        help_text=_("The payment method to use for this booking.")
    )
    phone_number = serializers.CharField(
        max_length=15,
        required=False,
        help_text=_("Phone number for M-Pesa payments (required for M-Pesa).")
    )
    
    def validate(self, data):
        """Validate payment initiation data."""
        booking_id = data.get('booking_id')
        payment_method = data.get('payment_method')
        phone_number = data.get('phone_number')
        
        # Check if booking exists
        try:
            booking_instance = booking.objects.get(id=booking_id)
        except booking.DoesNotExist:
            raise serializers.ValidationError(_("Booking not found."))
        
        # Check if booking can accept payment
        if booking_instance.status in ['cancelled', 'completed']:
            raise serializers.ValidationError(
                _("Cannot initiate payment for cancelled or completed bookings.")
            )
        
        if booking_instance.payment_status == 'paid':
            raise serializers.ValidationError(
                _("Payment has already been completed for this booking.")
            )
        
        # Validate phone number for M-Pesa
        if payment_method == 'mpesa':
            if not phone_number:
                raise serializers.ValidationError(
                    _("Phone number is required for M-Pesa payments.")
                )
            
            # Format and validate Kenyan phone number
            phone_number = self._format_phone_number(phone_number)
            data['phone_number'] = phone_number
        
        return data
    
    def _format_phone_number(self, phone):
        """Format phone number to Kenyan standard."""
        if not phone:
            return None
            
        # Remove any non-digit characters
        phone = ''.join(filter(str.isdigit, phone))
        
        # Handle different formats
        if phone.startswith('0'):
            # Convert 07XXXXXXXX to 2547XXXXXXXX
            phone = '254' + phone[1:]
        elif phone.startswith('7') and len(phone) == 9:
            # Convert 7XXXXXXXX to 2547XXXXXXXX
            phone = '254' + phone
        elif phone.startswith('+254'):
            # Convert +2547XXXXXXXX to 2547XXXXXXXX
            phone = phone[1:]
        elif not phone.startswith('254') and len(phone) == 9:
            # Add country code
            phone = '254' + phone
        
        # Validate length
        if len(phone) != 12 or not phone.startswith('254'):
            raise serializers.ValidationError(_("Invalid phone number format."))
        
        return phone

class PaymentStatusSerializer(serializers.Serializer):
    """
    Serializer for checking payment status.
    """
    booking_id = serializers.IntegerField(
        help_text=_("The ID of the booking to check payment status for.")
    )
    
    def validate_booking_id(self, value):
        """Validate that booking exists."""
        try:
            booking.objects.get(id=value)
        except booking.DoesNotExist:
            raise serializers.ValidationError(_("Booking not found."))
        return value