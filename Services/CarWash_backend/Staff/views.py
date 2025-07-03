from profile import Profile
from django.shortcuts import render
from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import StaffProfile, Task
from .serializer import StaffLoginSerializer, StaffProfileSerializer, StaffRegistrationSerializer
from rest_framework_simplejwt.tokens import RefreshToken,AccessToken,TokenError
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response
from rest_framework import status
from  Tenant.serializer import TaskSerializer

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
# logout view
class StaffLogoutView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            return Response({'detail': _('Refresh token is required.')}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'detail': _('Successfully logged out.')}, status=status.HTTP_205_RESET_CONTENT)
        except TokenError:
            return Response({'detail': _('Invalid refresh token.')}, status=status.HTTP_400_BAD_REQUEST)


#view to handle staff profile update
class StaffProfileUpdateView(generics.UpdateAPIView):
    serializer_class = StaffProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Return the staff profile associated with the authenticated user."""
        user = self.request.user
        return StaffProfile.objects.get(user=user)


#view to handle staff tasks retrieval
class StaffTaskListView(generics.ListAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        """Return tasks assigned to the authenticated staff member."""
        user = self.request.user
        return Task.objects.filter(assigned_to__user=user).order_by('-created_at')
