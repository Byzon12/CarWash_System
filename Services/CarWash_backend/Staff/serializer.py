
from os import read
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.hashers import make_password
from .models import StaffProfile
from Tenant.models import Tenant, Task
from  django.contrib.auth.hashers import check_password
from .models import Staff





#serializer class for staff profile
class StaffProfileSerializer(serializers.ModelSerializer):
  

    class Meta:
        model = StaffProfile
        fields = ['username', 'work_email', 'role', 'phone_number', 'email']
        
        
#serializer to handle staff password reset
class StaffPasswordResetSerializer(serializers.Serializer):
    """
    Serializer for staff password reset.
    This serializer is used to validate the new password for a staff member.
    It includes fields for the new password and confirms that the new password matches.
    """
    new_password = serializers.CharField(
        max_length=128,
        write_only=True,
        error_messages={
            'blank': _('New password cannot be blank.'),
            'max_length': _('New password cannot exceed 128 characters.')
        }
    )
    confirm_password = serializers.CharField(
        max_length=128,
        write_only=True,
        error_messages={
            'blank': _('Confirm password cannot be blank.'),
            'max_length': _('Confirm password cannot exceed 128 characters.')
        }
    )

    def validate(self, attrs):
        """
        Validate the new password and confirm password.
        """
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')

        if new_password != confirm_password:
            raise serializers.ValidationError(_('Passwords do not match.'))

        return attrs
    def save(self, staff):
        """
        Save the new password for the staff member.
        This method hashes the new password and updates the staff member's password.
        """
        new_password = self.validated_data['new_password']
        #hash the password before saving
        staff.password = new_password
        staff.save()
        return staff

        

# serializer class to handle staff login  using details from employee model
class StaffLoginSerializer(serializers.Serializer):
    """
    Serializer for staff login.
    This serializer is used to validate the login credentials of a staff member.
    It includes fields for username and password, and it validates that the user exists.
    """
    username = serializers.CharField(
        max_length=150,
        error_messages={
            'blank': _('Username cannot be blank.'),
            'max_length': _('Username cannot exceed 150 characters.')
        }
    )
    password = serializers.CharField(
        max_length=128,
        write_only=True,
        error_messages={
            'blank': _('Password cannot be blank.'),
            'max_length': _('Password cannot exceed 128 characters.')
        }
    )

        
    def validate(self, attrs):
        """
        Validate the login credentials.
        This method checks if the user exists and if the password is correct.
        """
        username = attrs.get('username')
        password = attrs.get('password')

       #check if username and password are provided
        if not username or not password:
            raise serializers.ValidationError(_('Username and password are required.'))
        
        try:
            staff_profile = StaffProfile.objects.get(username=username)
        except StaffProfile.DoesNotExist:
            raise serializers.ValidationError(_('Invalid username or password.'))

        staff = staff_profile.staff
        # Check if the password is correct
        if not check_password(password, staff.password):
            raise serializers.ValidationError(_('Invalid username or password.'))
        #store for later use

        attrs['staff'] = staff
        attrs['staff_profile'] = staff_profile

        return attrs
    
    def get_staff(self):
        """Return the authenticated staff user."""
        return self.validated_data.get('staff')

    def get_staff_profile(self):
        """Return serialized staff profile data."""
        staff_profile = self.validated_data.get('staff_profile')
        if staff_profile:
            return StaffProfileSerializer(staff_profile).data
        return None
    
#serializer to handle staff update profile
class StaffUpdateProfileSerializer(serializers.ModelSerializer):
    """Serializer for updating staff profile.
This serializer is used to update the profile of a staff member. and get the staff profile details.
It includes fields for email, phone number, work email, first name, and last name.  """
#read only fields
    staff = serializers.ReadOnlyField(source='staff.username')
    tenant = serializers.ReadOnlyField(source='tenant.name')
    location = serializers.ReadOnlyField(source='location.name')
    role = serializers.ReadOnlyField(source='role.role_type')
    salary = serializers.ReadOnlyField(source='role.salary')
    class Meta:
        model = StaffProfile
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'username', 'role', 'tenant', 'location',]

    def validate(self, attrs):
        # Validate the staff profile update.
        #check if the email is already in use by another staff member
        #during the check dont include the current staff member's email
        email = attrs.get('email')
        if email and StaffProfile.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError(_('Email is already in use.'))
        
        #check if the phone number is already in use by another staff member
        #during the check dont include the current staff member's phone number
        
        phone_number = attrs.get('phone_number')
        if phone_number and StaffProfile.objects.filter(phone_number=phone_number).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError(_('Phone number is already in use.')) 
        
        return attrs
    
    #override the update methodto update the staff member's profile
    def update(self, instance, validated_data):
        # Update the staff profile fields
        instance.email = validated_data.get('email', instance.email)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.work_email = validated_data.get('work_email', instance.work_email)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.save()
        return instance