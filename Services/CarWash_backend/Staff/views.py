from profile import Profile
from django.shortcuts import render
from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import StaffProfile
from Tenant.models import Task
from .serializer import StaffLoginSerializer, StaffProfileSerializer, StaffRegistrationSerializer
from rest_framework_simplejwt.tokens import RefreshToken,AccessToken,TokenError
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response
from rest_framework import status
from  Tenant.serializer import TaskSerializer
from .Authentication import StaffAuthentication

#from .Authentication import StaffAuthentication

#VIew to handle staff password registering
class StaffRegistrationView(generics.GenericAPIView):
    serializer_class = StaffRegistrationSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        staff = serializer.get_staff()
        return Response(StaffProfileSerializer(staff).data, status=201)

# API view to handle staff login with the username and password
class StaffLoginView(generics.GenericAPIView):
    serializer_class = StaffLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        staff = serializer.get_staff()

        refresh = RefreshToken()
        refresh['user_id'] = (staff.id)

        return Response({
            'token': str(refresh),
            'access': str(refresh.access_token),
            'staff': serializer.get_staff_profile()
            
        }, status=200)
# logout view
class StaffLogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

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
   # authentication_classes = [StaffAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Return the staff profile associated with the authenticated user."""
        staff = self.request.user
        return StaffProfile.objects.get(user=staff)


#view to handle staff tasks retrieval
class StaffTaskListView(generics.ListAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Return the list of tasks assigned to the authenticated staff member.
        The queryset is filtered by the tenant and location of the staff member.
        """
        staff = self.request.user # assuming the user is a staff member
        staff_profile = StaffProfile.objects.get(user=staff)
        return Task.objects.filter(tenant=staff_profile.tenant, location=staff_profile.location).order_by('-created_at')
    
class staffDashboardView(generics.GenericAPIView):
    """
    View to handle staff dashboard data retrieval.
    This view returns the staff profile and a list of tasks assigned to the staff member.
    """
    authentication_classes = [StaffAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """
        Return the staff profile associated with the authenticated user.
        """
        staff = self.request.user
        return StaffProfile.objects.get(user=staff)