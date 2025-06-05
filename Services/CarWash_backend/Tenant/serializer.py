
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db.models import Q
from Tenant.models import TenantProfile


# TenantProfile Serializer
class TenantProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for TenantProfile model.
    """
    class Meta:
        model = TenantProfile
        fields = (
            'id', 'username', 'first_name', 'last_name', 'email'
        )
        read_only_fields = ('created_at', 'updated_at')