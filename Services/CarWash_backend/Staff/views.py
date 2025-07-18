from profile import Profile
from tarfile import data_filter
from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from django.db import models, transaction
from .models import StaffProfile, WalkInCustomer, WalkInTask
from Tenant.models import Task
from .serializer import (
    StaffLoginSerializer, StaffProfileSerializer, StaffUpdateProfileSerializer, 
    StaffPasswordResetSerializer, StaffTaskSerializer, StaffUpdateTaskStatusSerializer,
    WalkInCustomerSerializer, WalkInTaskSerializer, WalkInTaskStatusSerializer,
    WalkInPaymentSerializer, MpesaPaymentInitiateSerializer, PaymentStatusSerializer, WalkInTaskTemplateSerializer
)
from .models import WalkInPayment,  WalkInTaskTemplate
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from Tenant.serializer import TaskSerializer
from .Authentication import StaffAuthentication
from .payment_gateways.walkin_mpesa import walkin_mpesa_service

# Enhanced API view to handle staff login
class StaffLoginView(generics.GenericAPIView):
    """Enhanced staff login with comprehensive mobile response."""
    serializer_class = StaffLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """Handle staff login with enhanced response."""
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                staff = serializer.get_staff()
                staff_profile = serializer.get_staff_profile()
                
                # Generate tokens
                refresh = RefreshToken()
                refresh['user_id'] = staff.id
                
                # Remember me functionality
                remember_me = serializer.validated_data.get('remember_me', False)
                if remember_me:
                    refresh.set_exp(lifetime=refresh.lifetime * 7)  # 7x longer expiry
                
                return Response({
                    'success': True,
                    'message': 'Login successful',
                    'data': {
                        'token': str(refresh),
                        'access': str(refresh.access_token),
                        'staff_profile': staff_profile,
                        'permissions': {
                            'can_manage_walkins': True,
                            'can_update_tasks': True,
                            'is_manager': staff_profile.get('is_manager', False)
                        }
                    }
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': 'Login failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred during login',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Enhanced logout view
class StaffLogoutView(generics.GenericAPIView):
    """Enhanced staff logout with proper token blacklisting."""
    authentication_classes = [StaffAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """Handle staff logout with enhanced response."""
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                return Response({
                    'success': False,
                    'message': 'Refresh token is required',
                    'error': 'Missing refresh token'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({
                'success': True,
                'message': 'Successfully logged out'
            }, status=status.HTTP_200_OK)
            
        except TokenError:
            return Response({
                'success': False,
                'message': 'Invalid refresh token',
                'error': 'Token validation failed'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred during logout',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Enhanced API view to handle staff password reset
class StaffPasswordResetView(generics.UpdateAPIView):
    """Enhanced staff password reset with better validation."""
    serializer_class = StaffPasswordResetSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]

    def get_object(self):
        """Return the staff profile of the authenticated user."""
        staff_user = self.request.user
        try:
            return StaffProfile.objects.get(staff=staff_user)
        except StaffProfile.DoesNotExist:
            return None

    def put(self, request, *args, **kwargs):
        """Handle password reset with enhanced response."""
        try:
            staff_profile = self.get_object()
            if not staff_profile:
                return Response({
                    'success': False,
                    'message': 'Staff profile not found',
                    'error': 'Profile does not exist'
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save(staff=staff_profile.staff)
                return Response({
                    'success': True,
                    'message': 'Password reset successfully'
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': 'Password reset failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred during password reset',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Enhanced API view to handle staff profile retrieval and update
class StaffProfileView(generics.RetrieveUpdateAPIView):
    """Enhanced staff profile management with mobile optimization."""
    serializer_class = StaffUpdateProfileSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]

    def get_object(self):
        """Return the staff profile of the authenticated user."""
        staff_user = self.request.user
        try:
            return StaffProfile.objects.get(staff=staff_user)
        except StaffProfile.DoesNotExist:
            return None
    
    def get(self, request, *args, **kwargs):
        """Handle profile retrieval with enhanced response."""
        try:
            staff_profile = self.get_object()
            if not staff_profile:
                return Response({
                    'success': False,
                    'message': 'Staff profile not found',
                    'error': 'Profile does not exist'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = self.get_serializer(staff_profile)
            return Response({
                'success': True,
                'message': 'Profile retrieved successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while retrieving profile',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, *args, **kwargs):
        """Handle profile update with enhanced response."""
        try:
            staff_profile = self.get_object()
            if not staff_profile:
                return Response({
                    'success': False,
                    'message': 'Staff profile not found',
                    'error': 'Profile does not exist'
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = self.get_serializer(staff_profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'message': 'Profile updated successfully',
                    'data': serializer.data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': 'Profile update failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while updating profile',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Enhanced view to handle staff tasks retrieval
class StaffTaskListView(generics.ListAPIView):
    """Enhanced staff task listing with filtering and pagination."""
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]

    def get_queryset(self):
        """Return filtered tasks for the authenticated staff member."""
        staff_user = self.request.user
        
        try:
            staff_profile = StaffProfile.objects.get(staff=staff_user)
        except StaffProfile.DoesNotExist:
            return Task.objects.none()

        queryset = Task.objects.filter(assigned_to=staff_profile).order_by('-created_at')
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Handle task listing with enhanced response."""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            return Response({
                'success': True,
                'message': 'Tasks retrieved successfully',
                'data': serializer.data,
                'count': queryset.count()
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while retrieving tasks',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Enhanced API view to handle staff task statistics
class StaffTaskStatisticsView(generics.RetrieveAPIView):
    """Enhanced staff dashboard with task and walk-in statistics."""
    serializer_class = StaffTaskSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]

    def get_object(self):
        """Return the staff profile of the authenticated user."""
        staff_user = self.request.user
        try:
            return StaffProfile.objects.get(staff=staff_user)
        except StaffProfile.DoesNotExist:
            return None

    def get(self, request, *args, **kwargs):
        """Handle statistics retrieval with enhanced response."""
        try:
            staff_profile = self.get_object()
            if not staff_profile:
                return Response({
                    'success': False,
                    'message': 'Staff profile not found',
                    'error': 'Profile does not exist'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Create serializer instance and get data directly from staff profile
            serializer = self.get_serializer()
            serialized_data = serializer.to_representation(staff_profile)
            
            return Response({
                'success': True,
                'message': 'Statistics retrieved successfully',
                'data': serialized_data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while retrieving statistics',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Enhanced API view to handle updating task status
class StaffUpdateTaskStatusView(generics.UpdateAPIView):
    """Enhanced task status update with better validation."""
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
    
    def update(self, request, *args, **kwargs):
        """Handle task status update with enhanced response."""
        try:
            partial = kwargs.pop('partial', True)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            
            if serializer.is_valid():
                self.perform_update(serializer)
                return Response({
                    'success': True,
                    'message': 'Task status updated successfully',
                    'data': serializer.data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': 'Task status update failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while updating task status',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Walk-in Customer Management Views
class WalkInCustomerCreateView(generics.CreateAPIView):
    """Create new walk-in customers for on-site operations."""
    serializer_class = WalkInCustomerSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def create(self, request, *args, **kwargs):
        """Handle walk-in customer creation with enhanced response."""
        try:
            with transaction.atomic():
                serializer = self.get_serializer(data=request.data)
                if serializer.is_valid():
                    customer = serializer.save()
                    return Response({
                        'success': True,
                        'message': 'Walk-in customer registered successfully',
                        'data': serializer.data
                    }, status=status.HTTP_201_CREATED)
                
                return Response({
                    'success': False,
                    'message': 'Walk-in customer registration failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while registering walk-in customer',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WalkInCustomerListView(generics.ListAPIView):
    """List walk-in customers with filtering options."""
    serializer_class = WalkInCustomerSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def get_queryset(self):
        """Return walk-in customers filtered by staff location/tenant."""
        staff_user = self.request.user
        
        try:
            staff_profile = StaffProfile.objects.get(staff=staff_user)
        except StaffProfile.DoesNotExist:
            return WalkInCustomer.objects.none()
        
        # Filter by staff location if available, otherwise by tenant
        if staff_profile.location:
            queryset = WalkInCustomer.objects.filter(location=staff_profile.location)
        else:
            queryset = WalkInCustomer.objects.filter(location__tenant=staff_profile.tenant)
        
        # Additional filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        today_only = self.request.query_params.get('today_only')
        if today_only == 'true':
            from django.utils import timezone
            today = timezone.now().date()
            queryset = queryset.filter(arrived_at__date=today)
        
        return queryset.order_by('-arrived_at')
    
    def list(self, request, *args, **kwargs):
        """Handle walk-in customer listing with enhanced response."""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            return Response({
                'success': True,
                'message': 'Walk-in customers retrieved successfully',
                'data': serializer.data,
                'count': queryset.count()
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while retrieving walk-in customers',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WalkInCustomerUpdateView(generics.UpdateAPIView):
    """Update walk-in customer status and details."""
    serializer_class = WalkInCustomerSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def get_queryset(self):
        """Return walk-in customers accessible to the staff member."""
        staff_user = self.request.user
        
        try:
            staff_profile = StaffProfile.objects.get(staff=staff_user)
        except StaffProfile.DoesNotExist:
            return WalkInCustomer.objects.none()
        
        if staff_profile.location:
            return WalkInCustomer.objects.filter(location=staff_profile.location)
        else:
            return WalkInCustomer.objects.filter(location__tenant=staff_profile.tenant)
    
    def update(self, request, *args, **kwargs):
        """Handle walk-in customer update with status timing."""
        try:
            partial = kwargs.pop('partial', True)
            instance = self.get_object()
            old_status = instance.status
            
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            
            if serializer.is_valid():
                # Handle status-based timing
                new_status = serializer.validated_data.get('status', old_status)
                
                if old_status == 'waiting' and new_status == 'in_service':
                    instance.service_started_at = timezone.now()
                elif old_status == 'in_service' and new_status == 'completed':
                    instance.service_completed_at = timezone.now()
                
                self.perform_update(serializer)
                
                return Response({
                    'success': True,
                    'message': 'Walk-in customer updated successfully',
                    'data': serializer.data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': 'Walk-in customer update failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while updating walk-in customer',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WalkInTaskCreateView(generics.CreateAPIView):
    """Create tasks for walk-in customers with enhanced validation."""
    serializer_class = WalkInTaskSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def create(self, request, *args, **kwargs):
        """Handle walk-in task creation with enhanced response."""
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                task = serializer.save()
                
                return Response({
                    'success': True,
                    'message': 'Walk-in task created successfully',
                    'data': serializer.data,
                    'task_id': task.id
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                'success': False,
                'message': 'Walk-in task creation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while creating walk-in task',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WalkInTaskListView(generics.ListAPIView):
    """Enhanced list view for walk-in tasks with filtering."""
    serializer_class = WalkInTaskSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def get_queryset(self):
        """Return filtered walk-in tasks."""
        staff_user = self.request.user
        
        try:
            staff_profile = StaffProfile.objects.get(staff=staff_user)
        except StaffProfile.DoesNotExist:
            return WalkInTask.objects.none()
        
        # Base queryset - tasks assigned to staff
        queryset = WalkInTask.objects.filter(assigned_to=staff_profile).select_related(
            'walkin_customer', 'assigned_to', 'created_by', 'prerequisite_task'
        )
        
        # Apply filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        priority_filter = self.request.query_params.get('priority')
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            queryset = queryset.filter(walkin_customer_id=customer_id)
        
        # Date filters
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        # Show only active tasks or include completed
        include_completed = self.request.query_params.get('include_completed', 'false')
        if include_completed.lower() != 'true':
            queryset = queryset.exclude(status__in=['completed', 'cancelled'])
        
        # Ordering
        ordering = self.request.query_params.get('ordering', '-created_at')
        if ordering in ['created_at', '-created_at', 'priority', '-priority', 'status']:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('-created_at')
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Handle task listing with enhanced response and statistics."""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            # Calculate statistics
            all_tasks = WalkInTask.objects.filter(assigned_to__staff=request.user)
            stats = {
                'total_tasks': all_tasks.count(),
                'pending_tasks': all_tasks.filter(status='pending').count(),
                'in_progress_tasks': all_tasks.filter(status='in_progress').count(),
                'completed_tasks': all_tasks.filter(status='completed').count(),
                'overdue_tasks': sum(1 for task in all_tasks if task.is_overdue),
                'filtered_count': queryset.count(),
                'completion_rate': round(
                    (all_tasks.filter(status='completed').count() / all_tasks.count() * 100) 
                    if all_tasks.count() > 0 else 0, 2
                )
            }
            
            return Response({
                'success': True,
                'message': 'Walk-in tasks retrieved successfully',
                'data': serializer.data,
                'statistics': stats,
                'filters_applied': {
                    'status': request.query_params.get('status'),
                    'priority': request.query_params.get('priority'),
                    'customer_id': request.query_params.get('customer_id'),
                    'include_completed': request.query_params.get('include_completed', 'false')
                }
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while retrieving walk-in tasks',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WalkInTaskUpdateView(generics.UpdateAPIView):
    """Enhanced update view for walk-in tasks."""
    serializer_class = WalkInTaskSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def get_queryset(self):
        """Return walk-in tasks accessible to the staff member."""
        staff_user = self.request.user
        
        try:
            staff_profile = StaffProfile.objects.get(staff=staff_user)
        except StaffProfile.DoesNotExist:
            return WalkInTask.objects.none()
        
        # Allow access to tasks assigned to the staff or created by them
        return WalkInTask.objects.filter(
            models.Q(assigned_to=staff_profile) | models.Q(created_by=staff_profile)
        )
    
    def update(self, request, *args, **kwargs):
        """Handle task update with enhanced validation and response."""
        try:
            partial = kwargs.pop('partial', True)
            instance = self.get_object()
            old_status = instance.status
            
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            
            if serializer.is_valid():
                updated_task = serializer.save()
                
                # Check if status changed and handle accordingly
                new_status = updated_task.status
                status_changed = old_status != new_status
                
                response_data = serializer.data
                if status_changed:
                    response_data['status_change'] = {
                        'from': old_status,
                        'to': new_status,
                        'timestamp': timezone.now().isoformat()
                    }
                
                return Response({
                    'success': True,
                    'message': f'Walk-in task {"status " if status_changed else ""}updated successfully',
                    'data': response_data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': 'Walk-in task update failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while updating walk-in task',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WalkInTaskDetailView(generics.RetrieveAPIView):
    """Enhanced detail view for walk-in tasks."""
    serializer_class = WalkInTaskSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def get_queryset(self):
        """Return walk-in tasks accessible to the staff member."""
        staff_user = self.request.user
        
        try:
            staff_profile = StaffProfile.objects.get(staff=staff_user)
        except StaffProfile.DoesNotExist:
            return WalkInTask.objects.none()
        
        return WalkInTask.objects.filter(
            models.Q(assigned_to=staff_profile) | models.Q(created_by=staff_profile)
        ).select_related('walkin_customer', 'assigned_to', 'created_by', 'prerequisite_task')
    
    def retrieve(self, request, *args, **kwargs):
        """Handle task detail retrieval with customer info and related tasks."""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            
            # Get customer details
            customer_serializer = WalkInCustomerSerializer(instance.walkin_customer)
            
            # Get related tasks for same customer
            related_tasks = WalkInTask.objects.filter(
                walkin_customer=instance.walkin_customer
            ).exclude(id=instance.id).order_by('-created_at')[:5]
            
            related_tasks_serializer = WalkInTaskSerializer(related_tasks, many=True)
            
            # Get dependent tasks (tasks that depend on this one)
            dependent_tasks = WalkInTask.objects.filter(
                prerequisite_task=instance
            ).order_by('-created_at')
            
            dependent_tasks_serializer = WalkInTaskSerializer(dependent_tasks, many=True)
            
            response_data = serializer.data
            response_data['customer_details'] = customer_serializer.data
            response_data['related_tasks'] = related_tasks_serializer.data
            response_data['dependent_tasks'] = dependent_tasks_serializer.data
            
            return Response({
                'success': True,
                'message': 'Walk-in task details retrieved successfully',
                'data': response_data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while retrieving task details',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WalkInTaskStatusUpdateView(generics.UpdateAPIView):
    """Quick status update for walk-in tasks."""
    serializer_class = WalkInTaskStatusSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def get_queryset(self):
        """Return walk-in tasks for the authenticated staff member."""
        staff_user = self.request.user
        
        try:
            staff_profile = StaffProfile.objects.get(staff=staff_user)
        except StaffProfile.DoesNotExist:
            return WalkInTask.objects.none()
        
        return WalkInTask.objects.filter(assigned_to=staff_profile)
    
    def update(self, request, *args, **kwargs):
        """Handle quick status update."""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(data=request.data)
            
            if serializer.is_valid():
                # Update task fields
                for field, value in serializer.validated_data.items():
                    setattr(instance, field, value)
                
                # Handle status-specific updates
                if 'status' in serializer.validated_data:
                    new_status = serializer.validated_data['status']
                    
                    if instance.status == 'pending' and new_status == 'in_progress':
                        instance.start_task()
                    elif instance.status == 'in_progress' and new_status == 'completed':
                        final_price = serializer.validated_data.get('final_price')
                        quality_rating = serializer.validated_data.get('quality_rating')
                        instance.complete_task(final_price, quality_rating)
                    else:
                        instance.status = new_status
                        instance.save()
                
                # Return updated task data
                task_serializer = WalkInTaskSerializer(instance)
                
                return Response({
                    'success': True,
                    'message': f'Task status updated to {instance.get_status_display()}',
                    'data': task_serializer.data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': 'Status update failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while updating task status',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WalkInTaskBulkUpdateView(generics.UpdateAPIView):
    """Bulk update multiple tasks."""
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def put(self, request, *args, **kwargs):
        """Handle bulk task updates."""
        try:
            task_ids = request.data.get('task_ids', [])
            update_data = request.data.get('update_data', {})
            
            if not task_ids:
                return Response({
                    'success': False,
                    'message': 'No task IDs provided'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get staff profile
            staff_profile = StaffProfile.objects.get(staff=request.user)
            
            # Get tasks assigned to this staff
            tasks = WalkInTask.objects.filter(
                id__in=task_ids,
                assigned_to=staff_profile
            )
            
            if not tasks.exists():
                return Response({
                    'success': False,
                    'message': 'No valid tasks found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Update tasks
            updated_count = 0
            for task in tasks:
                for field, value in update_data.items():
                    if hasattr(task, field):
                        setattr(task, field, value)
                task.save()
                updated_count += 1
            
            return Response({
                'success': True,
                'message': f'Successfully updated {updated_count} tasks',
                'updated_count': updated_count
            }, status=status.HTTP_200_OK)
        
        except StaffProfile.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Staff profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred during bulk update',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WalkInTaskTemplateListView(generics.ListAPIView):
    """List available task templates."""
    serializer_class = WalkInTaskTemplateSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def get_queryset(self):
        """Return templates for the staff's tenant."""
        try:
            staff_profile = StaffProfile.objects.get(staff=self.request.user)
            return WalkInTaskTemplate.objects.filter(
                tenant=staff_profile.tenant,
                is_active=True
            ).order_by('name')
        except StaffProfile.DoesNotExist:
            return WalkInTaskTemplate.objects.none()
    
    def list(self, request, *args, **kwargs):
        """Handle template listing."""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            return Response({
                'success': True,
                'message': 'Task templates retrieved successfully',
                'data': serializer.data,
                'count': queryset.count()
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while retrieving templates',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Walk-in Payment Views
class WalkInMpesaPaymentInitiateView(generics.CreateAPIView):
    """Initiate M-Pesa payment for walk-in customers."""
    serializer_class = MpesaPaymentInitiateSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def create(self, request, *args, **kwargs):
        """Handle M-Pesa payment initiation."""
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                # Extract validated data
                walkin_customer_id = serializer.validated_data['walkin_customer_id']
                phone_number = serializer.validated_data['phone_number']
                amount = serializer.validated_data['amount']
                description = serializer.validated_data['description']
                
                # Verify staff has access to this customer
                staff_profile = StaffProfile.objects.get(staff=request.user)
                customer = WalkInCustomer.objects.get(id=walkin_customer_id)
                
                # Check if staff can access this customer (same location/tenant)
                if staff_profile.location and customer.location != staff_profile.location:
                    return Response({
                        'success': False,
                        'message': 'You do not have access to this customer',
                        'error': 'Unauthorized access'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # Initiate M-Pesa payment
                response = walkin_mpesa_service.initiate_walkin_payment(
                    walkin_customer_id=walkin_customer_id,
                    phone_number=phone_number,
                    amount=amount,
                    description=description
                )
                
                if response.get('success'):
                    return Response({
                        'success': True,
                        'message': 'M-Pesa payment initiated successfully',
                        'data': {
                            'payment_id': response.get('payment_id'),
                            'checkout_request_id': response.get('checkout_request_id'),
                            'customer_message': response.get('customer_message'),
                            'payment_reference': response.get('payment_reference')
                        }
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'success': False,
                        'message': 'Failed to initiate M-Pesa payment',
                        'error': response.get('error')
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'success': False,
                'message': 'Invalid payment data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except StaffProfile.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Staff profile not found',
                'error': 'Authentication error'
            }, status=status.HTTP_404_NOT_FOUND)
        except WalkInCustomer.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Walk-in customer not found',
                'error': 'Customer not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while initiating payment',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WalkInPaymentStatusView(generics.RetrieveAPIView):
    """Check payment status for walk-in customers."""
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def get(self, request, payment_id, *args, **kwargs):
        """Get payment status."""
        try:
            # Verify staff has access to this payment
            staff_profile = StaffProfile.objects.get(staff=request.user)
            payment = WalkInPayment.objects.get(id=payment_id)
            
            # Check if staff can access this payment (same location/tenant)
            if (staff_profile.location and 
                payment.walkin_customer.location != staff_profile.location):
                return Response({
                    'success': False,
                    'message': 'You do not have access to this payment',
                    'error': 'Unauthorized access'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Query M-Pesa status if payment is pending
            if payment.is_pending and payment.payment_method == 'mpesa':
                mpesa_response = walkin_mpesa_service.query_walkin_payment_status(payment_id)
                
                return Response({
                    'success': True,
                    'message': 'Payment status retrieved successfully',
                    'data': {
                        'payment_id': payment.id,
                        'status': payment.status,
                        'amount': payment.amount,
                        'amount_formatted': payment.amount_formatted,
                        'payment_method': payment.payment_method,
                        'transaction_id': payment.transaction_id,
                        'created_at': payment.created_at,
                        'completed_at': payment.completed_at,
                        'is_successful': payment.is_successful,
                        'is_pending': payment.is_pending,
                        'mpesa_status': mpesa_response if payment.payment_method == 'mpesa' else None
                    }
                }, status=status.HTTP_200_OK)
            else:
                # Return current status
                return Response({
                    'success': True,
                    'message': 'Payment status retrieved successfully',
                    'data': {
                        'payment_id': payment.id,
                        'status': payment.status,
                        'amount': payment.amount,
                        'amount_formatted': payment.amount_formatted,
                        'payment_method': payment.payment_method,
                        'transaction_id': payment.transaction_id,
                        'created_at': payment.created_at,
                        'completed_at': payment.completed_at,
                        'is_successful': payment.is_successful,
                        'is_pending': payment.is_pending
                    }
                }, status=status.HTTP_200_OK)
        
        except StaffProfile.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Staff profile not found',
                'error': 'Authentication error'
            }, status=status.HTTP_404_NOT_FOUND)
        except WalkInPayment.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Payment not found',
                'error': 'Payment not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while retrieving payment status',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WalkInPaymentListView(generics.ListAPIView):
    """List payments for walk-in customers."""
    serializer_class = WalkInPaymentSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def get_queryset(self):
        """Return payments filtered by staff location/tenant."""
        staff_user = self.request.user
        
        try:
            staff_profile = StaffProfile.objects.get(staff=staff_user)
        except StaffProfile.DoesNotExist:
            return WalkInPayment.objects.none()
        
        # Filter by staff location if available, otherwise by tenant
        if staff_profile.location:
            queryset = WalkInPayment.objects.filter(
                walkin_customer__location=staff_profile.location
            ).select_related('walkin_customer', 'processed_by')
        else:
            queryset = WalkInPayment.objects.filter(
                walkin_customer__location__tenant=staff_profile.tenant
            ).select_related('walkin_customer', 'processed_by')
        
        # Additional filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        payment_method_filter = self.request.query_params.get('payment_method')
        if payment_method_filter:
            queryset = queryset.filter(payment_method=payment_method_filter)
        
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            queryset = queryset.filter(walkin_customer_id=customer_id)
        
        return queryset.order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """Handle payment listing with enhanced response."""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            # Calculate summary statistics
            total_payments = queryset.count()
            successful_payments = queryset.filter(status='completed').count()
            pending_payments = queryset.filter(status__in=['pending', 'processing']).count()
            failed_payments = queryset.filter(status__in=['failed', 'cancelled']).count()
            
            total_amount = sum(payment.amount for payment in queryset if payment.status == 'completed')
            
            return Response({
                'success': True,
                'message': 'Payments retrieved successfully',
                'data': serializer.data,
                'summary': {
                    'total_payments': total_payments,
                    'successful_payments': successful_payments,
                    'pending_payments': pending_payments,
                    'failed_payments': failed_payments,
                    'total_amount': total_amount,
                    'total_amount_formatted': f"KSh {total_amount:,.2f}"
                }
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while retrieving payments',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



