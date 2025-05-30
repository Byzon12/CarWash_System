from rest_framework import serializers

from .models import User
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'is_staff', 'is_active', 'role', 'date_joined']
        read_only_fields = ['id', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': False}
        }
    def create(self, validated_data):
        user =User.objects.create_user(**validated_data)
        return user