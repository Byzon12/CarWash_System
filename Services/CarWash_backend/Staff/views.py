from profile import Profile
from django.shortcuts import render
from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import StaffProfile
from .serializer import StaffLoginSerializer, StaffProfileSerializer, StaffRegistrationSerializer
from rest_framework_simplejwt.tokens import RefreshToken,AccessToken,TokenError
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

#VIew to handle staff password registering
class StaffRegistrationView(generics.GenericAPIView):
    serializer_class = StaffRegistrationSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        staff_profile = serializer.save()
        return Response(StaffProfileSerializer(staff_profile).data, status=201)

# API view to handle staff login with the username and password
class StaffLoginView(generics.GenericAPIView):
    serializer_class = StaffLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        staff_profile = serializer.get_staff_profile()

        refresh = RefreshToken()
        refresh['staff_profile'] = staff_profile.id
        serialized_profile = StaffProfileSerializer(staff_profile).data
        return Response({
            'token': str(refresh),
            'access': str(refresh.access_token),
            'staff_profile': serialized_profile
        }, status=200)
# Create your views here.


