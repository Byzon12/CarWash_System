
from email import message
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db.models import Q
from Tenant.models import TenantProfile


# TenantProfile Serializer
class TenantUpdateProfileSerializer(serializers.ModelSerializer):
    logo =serializers.ImageField(
        error_messages ={
            'blank': _('logo cannot be blank.'),
            'invalid': _('Enter a valid Image')
        }
    )
    class Meta:
        model = TenantProfile
        fields = '__all__'
        #Setting the create at and updated at as the read only field
        extra_kwargs ={
            'create_at':{'read_only': True},
            'updated_at':{'read_only': True}
        }
        # fuction to validate the fields 
        