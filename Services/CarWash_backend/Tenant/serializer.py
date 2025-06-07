
from email import message
from urllib import request
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db.models import Q
from Tenant.models import TenantProfile
from django.contrib.auth.hashers import check_password

# serializer to handle Tenant login with the username and password
class TenantLoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=150,
        min_length=3,
        validators=[UnicodeUsernameValidator()],
        error_messages={
            'blank': _('Username cannot be blank.'),
            'max_length': _('Username cannot exceed 150 characters.'),
            'min_length': _('Username must be at least 3 characters long.')
        }
    )
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        error_messages={
            'blank': _('Password cannot be blank.')
        }
    )

    def validate(self, data):
        """Validate the username and password."""
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            raise serializers.ValidationError(_('Username and password are required.'))
        
        try:
            tenant_profile = TenantProfile.objects.get(
                Q(business_email=username) | Q(username=username)
            )
           
        except TenantProfile.DoesNotExist:
            raise serializers.ValidationError(_('Invalid username or password.'))

        tenant = tenant_profile.tenant
        if not check_password(password, tenant.password):
            raise serializers.ValidationError(_('Invalid username or password.'))
        data['tenant'] = tenant
        data['tenant_profile'] = tenant_profile

        return data
    # method to return the tenant profile
    def get_tenant_profile(self):
        """Return the tenant profile associated with the validated data."""
        tenant = self.validated_data.get('tenant', None)
        if tenant:
            return {
                'id': tenant.pk,
                'name': tenant.name,
                'tenant_profile': {
                    'id': self.validated_data['tenant_profile'].pk,
                        'business_name': self.validated_data['tenant_profile'].business_name,
                        'business_email': self.validated_data['tenant_profile'].business_email,
                        'phone_number': self.validated_data['tenant_profile'].phone_number,
                        'address': self.validated_data['tenant_profile'].address,
                        'created_at': self.validated_data['tenant_profile'].created_at,
                        'updated_at': self.validated_data['tenant_profile'].updated_at
                    }
                }


    
    def get_tenant(self):
       return self.validated_data.get('tenant', None)

    # method to return the tenant profile


# TenantProfile Serializer
class TenantProfileSerializer(serializers.ModelSerializer):
    tenant = serializers.StringRelatedField(read_only=True)
    name = serializers.CharField(source='tenant.name', read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = TenantProfile
        fields = '__all__'
     
    # method to validate bussiness email, bussiness_name and phone number

    def validate(self, data):
        """custom validation to ensure business email, business name and phone number are valid and unique."""
        phone_number = data.get('phone_number')
        # validate bussiness email if it ends with @tenant.com
        business_email = data.get('bussiness_email')
        if business_email and not business_email.endswith('@tenant.com'):
            raise serializers.ValidationError({
                'bussiness_email': _('Business email must be a valid tenant email.')
            })
        # validate phone number if it is not empty and does not start with +254
        if phone_number and not phone_number.startswith('+254'):
            raise serializers.ValidationError({
                'phone_number':( _('Phone number must be in international format. must start with +254.'))
            })
      
        return data

    # validate if the business name is already taken
    def validate_business_name(self, value):
        if TenantProfile.objects.filter(business_name__iexact=value).exists():
            raise serializers.ValidationError(_('Business name already exists.'))
        return value

# perform update method to ensure that the tenant profile is updated correctly
    def update(self, instance, validated_data):# -> Any:
        """Update the tenant profile instance with validated data."""
        # Update the tenant profile instance with the validated data
        validated_data['tenant'] = self.context.get('request').tenant if hasattr(self.context.get('request'), 'tenant') else None
        return super().update(instance, validated_data)

    def create(self, validated_data):
        """Create a new tenant profile instance."""
        request = self.context.get('request')
        tenant = request.tenant if hasattr(request, 'tenant') else None
        if not tenant:
            raise ValidationError(_('Tenant must be set.'))
        validated_data['tenant'] = tenant
        return super().create(validated_data)
