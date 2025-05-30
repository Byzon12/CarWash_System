from rest_framework import serializers

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import make_password

User = get_user_model()
from .models import User
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'is_staff', 'is_active', 'role', 'date_joined', 'password', 'confirm_password']
        read_only_fields = ['id', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': True}
        }
        
        # serializer method to ensure that the password and confirm password are the same
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        
        # Validate the password using Django's built-in validators
        validate_password(data['password'])
        
        return data
    def create(self, validated_data):
        # Remove confirm_password from validated_data
        validated_data.pop('confirm_password', None)
        #hash the password field to ensure it is hashed
        user.set_password(validated_data['password'])
        validated_data['password'] = make_password(validated_data['password'])
        # Create the user with the validated data
    
        user =User.objects.create_user(**validated_data)
        return user