from ctypes import FormatError
from email import message
from os import read
from urllib import request
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db.models import Q

# Import models
from booking.models import Booking

# Serializer for Booking model
class BookingSerializer(serializers.ModelSerializer):
    """
    Serializer for Booking model.
    Handles validation and serialization of booking data.
    """
    class Meta:
        model = Booking
        fields = [
            'id', 'location', 'customer', 'location_service',
            'time_slot_start', 'time_slot_end', 'amount',
            'status', 'payment_method', 'payment_status',
            'payment_reference', 'is_prepaid', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'time_slot_end', 'created_at', 'updated_at']

    def validate(self, attrs):
        """
        Custom validation to ensure that the booking does not overlap with existing bookings.
        """
        location = attrs.get('location')
        time_slot_start = attrs.get('time_slot_start')

        if Booking.objects.filter(
            location=location,
            time_slot_start__lt=time_slot_start + attrs['location_service'].service.duration,
            time_slot_end__gt=time_slot_start
        ).exists():
            raise ValidationError(_("This time slot is already booked at this location."))

        return attrs
    
def create(self, validated_data):
        # Set the amount based on the service
        service = validated_data.get('location_service')
        validated_data['amount'] = service.price
        return super().create(validated_data)