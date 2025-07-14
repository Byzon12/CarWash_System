from profile import Profile
from tarfile import data_filter
from django.shortcuts import render
from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import StaffProfile
from Tenant.models import Task
from .serializer import StaffLoginSerializer, StaffProfileSerializer,   StaffUpdateProfileSerializer, StaffPasswordResetSerializer, StaffTaskSerializer,StaffUpdateTaskStatusSerializer
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response
from rest_framework import status
from  Tenant.serializer import TaskSerializer
from .Authentication import StaffAuthentication

#from .Authentication import StaffAuthentication



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
           # 'staff': serializer.get_staff_profile()
            
        }, status=200)
# logout view
class StaffLogoutView(generics.GenericAPIView):
    authentication_classes = [StaffAuthentication]
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
#api view to handle staff password reset
class StaffPasswordResetView(generics.UpdateAPIView):
    serializer_class = StaffPasswordResetSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]

    def get_object(self):
        """
        Return the staff profile of the authenticated user.
        """
        staff_user = self.request.user
        try:
            return StaffProfile.objects.get(staff=staff_user)
        except StaffProfile.DoesNotExist:
            return None

    def put(self, request, *args, **kwargs):
        """
        Handle PUT request to reset the staff password.
        """
        staff_profile = self.get_object()
        if not staff_profile:
            return Response({'detail': _('Staff profile not found.')}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(staff=staff_profile.staff)
        
        return Response({'detail': _('Password reset successfully.')}, status=status.HTTP_200_OK)


# API view to handle staff profile retrieval and update
class StaffProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = StaffUpdateProfileSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]

    def get_object(self):
        """
        Return the staff profile of the authenticated user.
        """
        staff_user = self.request.user
        try:
            return StaffProfile.objects.get(staff=staff_user)
        except StaffProfile.DoesNotExist:
            return None
    def get(self, request, *args, **kwargs):
        """
        Handle GET request to retrieve the staff profile.
        """
        staff_profile = self.get_object()
        if not staff_profile:
            return Response({'detail': _('Staff profile not found.')}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(staff_profile)
        return Response(serializer.data, status=status.HTTP_200_OK)
    def put(self, request, *args, **kwargs):
        """
        Handle PUT request to update the staff profile.
        """
        staff_profile = self.get_object()
        if not staff_profile:
            return Response({'detail': _('Staff profile not found.')}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(staff_profile, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


#view to handle staff tasks retrieval
class StaffTaskListView(generics.ListAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]


    def get_queryset(self):
        """
        Return the list of tasks assigned to the authenticated staff member.
        The queryset is filtered by the tenant and location of the staff member.
        """
        staff_user = self.request.user # assuming the user is a staff member
        
        try:
            staff_profile = StaffProfile.objects.get(staff=staff_user)
        except StaffProfile.DoesNotExist:
            return Task.objects.none()

        return Task.objects.filter(assigned_to=staff_profile).order_by('-created_at')
    
#api view to handle staff task statistics
class StaffTaskStatisticsView(generics.RetrieveAPIView):
    """
    API view to retrieve task statistics for the authenticated staff user.
    This view allows a staff member to fetch all tasks assigned to them. It uses custom authentication and permission classes to ensure only authenticated staff can access their own statistics.
    Methods:
        get_object():
            Retrieves the StaffProfile instance associated with the authenticated user.
            Returns None if the profile does not exist.
        get(request, *args, **kwargs):
            Handles GET requests to return serialized data of all tasks assigned to the staff user.
            Returns a 404 response if the staff profile is not found.
    Attributes:
        serializer_class (StaffTaskSerializer): Serializer for task data.
        permission_classes ([IsAuthenticated]): Ensures the user is authenticated.
        authentication_classes ([StaffAuthentication]): Custom authentication for staff users.
    """
    serializer_class = StaffTaskSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]

    def get_object(self):
        """
        Return the staff profile of the authenticated user.
        """
        staff_user = self.request.user
        try:
            return StaffProfile.objects.get(staff=staff_user)
        except StaffProfile.DoesNotExist:
            return None

    def get(self, request, *args, **kwargs):
        staff_profile = self.get_object()
        serializer = self.get_serializer(staff_profile)
        data = serializer.get_task_statistics(staff_profile)
        serializer_instance = StaffTaskSerializer(data)
        return Response(serializer_instance.data, status=status.HTTP_200_OK)

     
# API view to handle updating the status of a task assigned to a staff member
class StaffUpdateTaskStatusView(generics.UpdateAPIView):
    """
    API view to update the status of a task assigned to a staff member.
    This view allows a staff member to update the status of a task they are assigned to.
    """
    serializer_class = StaffUpdateTaskStatusSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def get_queryset(self):
        """Return tasks assigned to the authenticated staff member."""
        staff_user = self.request.user
        try:
            staff_profile = StaffProfile.objects.get(staff=staff_user)
            return Task.objects.filter(assigned_to=staff_profile)
        except StaffProfile.DoesNotExist:
            return Task.objects.none()


    
    