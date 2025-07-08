from ast import Is
from tkinter import E
import token
from urllib import request
from django.shortcuts import render
from django.forms import ValidationError
from rest_framework import generics, permissions, serializers, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Q
from django.db import models
from decimal import Decimal
from datetime import datetime, timedelta

from .models import Tenant, TenantProfile, Task
from .serializer import (
    TenantProfileSerializer, TenantLoginSerializer, EmployeeRoleSalarySerializer, 
    CreateEmployeeSerializer, TaskSerializer, TenantDashboardSerializer
)
from .email import send_tenant_profile_update_email
from Staff.models import StaffProfile, StaffRole

# Import models to avoid circular import issues
def get_location_model():
    from Location.models import Location
    return Location

def get_booking_model():
    from booking.models import Booking
    return Booking

# API view to handle tenant login
class TenantLoginView(generics.GenericAPIView):
    serializer_class = TenantLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
      
        tenant = serializer.get_tenant()
        refresh = RefreshToken()
        refresh['user_id'] = str(tenant.id)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'tenant': serializer.get_tenant_profile(),
            'message': _('Login successful.')
        }, status=status.HTTP_200_OK)

# Handle tenant logout
class TenantLogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({
                'detail': _('Refresh token is required for logout.')
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({
                'detail': _('Successfully logged out.')
            }, status=status.HTTP_200_OK)
        except TokenError:
            return Response({
                'detail': _('Token is already blacklisted or invalid.')
            }, status=status.HTTP_400_BAD_REQUEST)

class TenantProfileView(generics.RetrieveUpdateAPIView):
    """Handle retrieval and update of tenant profile."""
    serializer_class = TenantProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant = self.request.user
        return TenantProfile.objects.filter(tenant=tenant)

    def get_object(self):
        queryset = self.get_queryset()
        obj = queryset.first()
        if not obj:
            raise ValidationError(_('Tenant profile does not exist.'))
        return obj

class TenantProfileDetailsView(generics.RetrieveUpdateAPIView):
    serializer_class = TenantProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        tenant = self.request.user
        if not tenant or not isinstance(tenant, Tenant):
            raise ValidationError(_('Tenant must be authenticated.'))
        try:
            return TenantProfile.objects.get(tenant=tenant)
        except TenantProfile.DoesNotExist:
            raise ValidationError(_('Tenant profile does not exist.'))

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        send_tenant_profile_update_email(instance)
        return Response(serializer.data)

# Employee management views
class CreateEmployeeView(generics.CreateAPIView):
    serializer_class = CreateEmployeeSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        tenant = self.request.user
        serializer.save(tenant=tenant)

class ListEmployeeView(generics.ListAPIView):
    serializer_class = CreateEmployeeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant = self.request.user
        return StaffProfile.objects.filter(tenant=tenant)

class CreateEmployeeSalaryView(generics.CreateAPIView):
    """Handle creation of employee roles and their associated salaries."""
    serializer_class = EmployeeRoleSalarySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant = self.request.user
        return StaffRole.objects.filter(tenant=tenant)

    def perform_create(self, serializer):
        tenant = self.request.user
        Location = get_location_model()
        location_id = self.request.data.get('location')
        location = Location.objects.get(pk=location_id, tenant=tenant)
        serializer.save(tenant=tenant, location=location)

class DeleteEmployeeView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        pk = self.kwargs.get('pk')
        tenant = self.request.user
        try:
            return StaffProfile.objects.get(pk=pk, tenant=tenant)
        except StaffProfile.DoesNotExist:
            return None

    def delete(self, request, *args, **kwargs):
        employee = self.get_object()
        if not employee:
            return Response({
                'detail': _('Employee not found.')
            }, status=status.HTTP_404_NOT_FOUND)
        employee.delete()
        return Response({
            'detail': _('Employee deleted successfully.')
        }, status=status.HTTP_204_NO_CONTENT)

class DeactivateEmployeeView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        pk = self.kwargs.get('pk')
        tenant = self.request.user
        try:
            return StaffProfile.objects.get(pk=pk, tenant=tenant)
        except StaffProfile.DoesNotExist:
            return None

    def patch(self, request, *args, **kwargs):
        employee = self.get_object()
        if not employee:
            return Response({
                'detail': _('Employee not found.')
            }, status=status.HTTP_404_NOT_FOUND)
        employee.is_active = False
        employee.save()
        return Response({
            'detail': _('Employee deactivated successfully.')
        }, status=status.HTTP_200_OK)

class ActivateEmployeeView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        pk = self.kwargs.get('pk')
        tenant = self.request.user
        try:
            return StaffProfile.objects.get(pk=pk, tenant=tenant)
        except StaffProfile.DoesNotExist:
            return None

    def patch(self, request, *args, **kwargs):
        employee = self.get_object()
        if not employee:
            return Response({
                'detail': _('Employee not found.')
            }, status=status.HTTP_404_NOT_FOUND)
        employee.is_active = True
        employee.save()
        return Response({
            'detail': _('Employee activated successfully.')
        }, status=status.HTTP_200_OK)

# Task management views
class TaskCreateView(generics.CreateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        tenant = self.request.user
        return Task.objects.filter(tenant=tenant)

    def perform_create(self, serializer):
        tenant = self.request.user
        serializer.save(tenant=tenant)

class TaskListView(generics.ListAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        tenant = self.request.user
        return Task.objects.filter(tenant=tenant).order_by('-created_at')

class TaskDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        tenant = self.request.user
        return Task.objects.filter(tenant=tenant)

class TaskUpdateStatusView(generics.UpdateAPIView):
    """Update task status for tenant."""
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        pk = self.kwargs.get('pk')
        tenant = self.request.user
        try:
            return Task.objects.get(pk=pk, tenant=tenant)
        except Task.DoesNotExist:
            return None

    def patch(self, request, *args, **kwargs):
        task = self.get_object()
        if not task:
            return Response({
                'detail': _('Task not found.')
            }, status=status.HTTP_404_NOT_FOUND)
            
        new_status = request.data.get('status')
        if not new_status:
            return Response({
                'detail': _('Status is required.')
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Validate status transition
        valid_transitions = {
            'pending': ['in_progress', 'completed', 'overdue'],
            'in_progress': ['completed', 'overdue'],
            'completed': [],
            'overdue': ['completed']
        }
        
        if new_status not in valid_transitions.get(task.status, []):
            return Response({
                'detail': _('Invalid status transition.')
            }, status=status.HTTP_400_BAD_REQUEST)
            
        task.status = new_status
        task.save()
        
        serializer = TaskSerializer(task, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

# Dashboard and statistics views
class TenantDashboardStatsView(generics.GenericAPIView):
    """Get dashboard statistics for tenant."""
    serializer_class = TenantDashboardSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        tenant = request.user
        Location = get_location_model()
        Booking = get_booking_model()
        
        # Calculate statistics
        total_staff = StaffProfile.objects.filter(tenant=tenant).count()
        total_locations = Location.objects.filter(tenant=tenant).count()
        total_tasks = Task.objects.filter(tenant=tenant).count()
        
        # Task statistics
        pending_tasks = Task.objects.filter(tenant=tenant, status='pending').count()
        in_progress_tasks = Task.objects.filter(tenant=tenant, status='in_progress').count()
        completed_tasks = Task.objects.filter(tenant=tenant, status='completed').count()
        overdue_tasks = Task.objects.filter(tenant=tenant, status='overdue').count()
        
        # Booking statistics
        total_bookings = Booking.objects.filter(location__tenant=tenant).count()
        confirmed_bookings = Booking.objects.filter(location__tenant=tenant, status='confirmed').count()
        completed_bookings = Booking.objects.filter(location__tenant=tenant, status='completed').count()

        # Revenue calculation (this month)
        current_month = datetime.now().month
        current_year = datetime.now().year
        revenue_this_month = Booking.objects.filter(
            location__tenant=tenant,
            status='completed',
            created_at__month=current_month,
            created_at__year=current_year
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        data = {
            'total_staff': total_staff,
            'total_locations': total_locations,
            'total_tasks': total_tasks,
            'pending_tasks': pending_tasks,
            'in_progress_tasks': in_progress_tasks,
            'completed_tasks': completed_tasks,
            'overdue_tasks': overdue_tasks,
            'total_bookings': total_bookings,
            'confirmed_bookings': confirmed_bookings,
            'completed_bookings': completed_bookings,
            'revenue_this_month': revenue_this_month
        }
        
        serializer = self.get_serializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)

class StaffTaskStatisticsView(generics.GenericAPIView):
    """Get task statistics grouped by staff for tenant."""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        tenant = request.user
        
        staff_stats = StaffProfile.objects.filter(tenant=tenant).annotate(
            total_tasks=Count('tasks'),
            pending_tasks=Count('tasks', filter=Q(tasks__status='pending')),
            in_progress_tasks=Count('tasks', filter=Q(tasks__status='in_progress')),
            completed_tasks=Count('tasks', filter=Q(tasks__status='completed')),
            overdue_tasks=Count('tasks', filter=Q(tasks__status='overdue'))
        ).values(
            'id', 'username', 'first_name', 'last_name', 'email',
            'total_tasks', 'pending_tasks', 'in_progress_tasks', 
            'completed_tasks', 'overdue_tasks'
        )
        
        return Response(list(staff_stats), status=status.HTTP_200_OK)
