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
from .models import CustomerProfile
from .models import Location, LocationService

# Import models
from booking.models import Booking


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
        

        if booking_date <= timezone.now():
            raise serializers.ValidationError(_("Booking date must be in the future."))
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
        fields = ['booking_date', 'status', 'payment_status', 'payment_reference']
        read_only_fields = ['customer', 'location', 'created_at', 'updated_at']

    def validate(self, data):
        """Validate the written data for the booking."""
        booking_date = data.get('booking_date')
        
        # Check if the booking date is provided
        if not booking_date:
            raise serializers.ValidationError(_("Booking date is required."))
        
        # Check if the booking date is in the future
        if booking_date <= timezone.now():
            raise serializers.ValidationError(_("Booking date must be in the future."))
        
        return data