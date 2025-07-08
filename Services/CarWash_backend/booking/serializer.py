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
from .models import Location, LocationService, Booking

# Import models
from booking.models import Booking

class BookingSerializer(serializers.ModelSerializer):
    """
    Serializer for the Booking model.
    """
    class Meta:
        model = Booking
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

# serialier clas to create a booking
class BookingCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a booking.
    This serializer validates the booking date to ensure it is in the future
    and includes fields for the booking details.
    It does not allow modification of the booking status or payment status.
    It also ensures that the payment reference is unique.
    It is used to create a new booking instance.
    It includes fields for the location, customer, service package, booking date,
    amount, payment method, and whether the booking is prepaid.
    """
    location = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(),
      
        write_only=False,
        help_text=_("The car wash location where the booking is made.")
    )
    location_service = serializers.PrimaryKeyRelatedField(
        queryset=LocationService.objects.all(),
       
        write_only=False,
        help_text=_("The specific service package booked at this location.")
    )
    customer = serializers.PrimaryKeyRelatedField(
        read_only=True,
        help_text=_("The customer making the booking.")
    )

    class Meta:
        model = Booking
        fields = [
            'location',
            'status',
            'payment_status',
            'customer',
            'location_service',
            'booking_date',
            'amount',
            'payment_method',
            'is_prepaid'
        ]
        read_only_fields = ['status', 'payment_status', 'payment_reference', 'created_at', 'updated_at','amount', 'customer']

    def validate(self, data):
        """validate the written data for the booking."""
        locate_service = data.get('location_service')
        booking_date = data.get('booking_date')

        # Check if the location service is provided
        if not data.get('location'):
            raise serializers.ValidationError(_("Location is required."))
        if not locate_service:
            raise serializers.ValidationError(_("Location service is required."))
        
        #check if the location service provide belogns to the location
        if locate_service.location != data['location']:
            raise serializers.ValidationError(_("The selected service does not belong to the specified location."))
        # Check if the booking date is provided
        if not booking_date:
            raise serializers.ValidationError(_("Booking date is required."))
        # Check if the booking date is in the future
        

     #   if booking_date <= timezone.now():
          #  raise serializers.ValidationError(_("Booking date must be in the future."))
        # Check if the booking date conflicts with existing bookings
        existing_bookings = Booking.objects.filter(
            location=data['location'],
            booking_date=booking_date,
            status__in=['pending', 'confirmed']
        )

        if existing_bookings.exists():
            raise serializers.ValidationError(_("Booking date conflicts with existing bookings."))
        
        # set the amount based on the location service price
        data['amount'] = locate_service.price
        # Set the status to 'pending' by default
        data['status'] = 'pending'
        data['payment_status'] = 'pending'
        # Set the payment reference to None by default
        data['payment_reference'] = None
        # Set the is_prepaid field to False by default
        data['is_prepaid'] = False
        
    #

        return data
    def create(self, validated_data):
        """
        Create a new booking instance.
        
        """
        request = self.context.get('request')
        try:
            validated_data['customer'] = request.user.Customer_profile
        except CustomerProfile.DoesNotExist:
            raise serializers.ValidationError({"error": "No CustomerProfile associated with this user."})

        booking = Booking.objects.create(**validated_data)
        return booking


#class serialier to update a booking
class BookingUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating a booking.
    This serializer allows updating the booking date, status, payment status,
    and payment reference. It does not allow changing the customer or location.
    """
    class Meta:
        model = Booking
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
        existing_bookings = Booking.objects.filter(
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
        model = Booking
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
        model = Booking
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
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            raise serializers.ValidationError(_("Booking not found."))
        
        # Check if booking can accept payment
        if booking.status in ['cancelled', 'completed']:
            raise serializers.ValidationError(
                _("Cannot initiate payment for cancelled or completed bookings.")
            )
        
        if booking.payment_status == 'paid':
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
            Booking.objects.get(id=value)
        except Booking.DoesNotExist:
            raise serializers.ValidationError(_("Booking not found."))
        return value