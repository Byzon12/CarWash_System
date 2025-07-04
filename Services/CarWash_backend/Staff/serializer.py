
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.hashers import make_password
from .models import StaffProfile
from Tenant.models import Tenant, Task
from  django.contrib.auth.hashers import check_password
from .models import Staff




# serializer class to handle staff registration using details from employee model
class StaffRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        max_length=128,
        min_length=8,
        error_messages={
            'blank': _('Password cannot be blank.'),
        }
    )
    class Meta:
        model = StaffProfile
        fields = ['password']
        write_only_fields = ['password']
        
    def create(self, validated_data):
        """
        Create a new staff profile with the provided validated data.
        This method hashes the password before saving the staff profile.
        """
        password = validated_data.pop('password', None)
        if password:
            validated_data['password'] = make_password(password)
        
        staff_profile = StaffProfile.objects.create(**validated_data)
        return staff_profile
    


#serializer class for staff profile
class StaffProfileSerializer(serializers.ModelSerializer):
  

    class Meta:
        model = StaffProfile
        fields = ['username', 'work_email', 'role', 'phone_number', 'email']
        
    

        

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
    
  

    