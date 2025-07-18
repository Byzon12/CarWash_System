from profile import Profile
from tarfile import data_filter
from django.shortcuts import render
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
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
    """Create walk-in customer with automatic task creation."""
    serializer_class = WalkInCustomerSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def get_queryset(self):
        """Filter queryset based on staff location/tenant."""
        try:
            staff_profile = StaffProfile.objects.get(staff=self.request.user)
            if staff_profile.location:
                return WalkInCustomer.objects.filter(
                    location=staff_profile.location
                ).select_related('location', 'location_service', 'assigned_staff', 'created_by')
            else:
                return WalkInCustomer.objects.filter(
                    location__tenant=staff_profile.tenant
                ).select_related('location', 'location_service', 'assigned_staff', 'created_by')
        except StaffProfile.DoesNotExist:
            return WalkInCustomer.objects.none()
    
    def create(self, request, *args, **kwargs):
        """Create walk-in customer with automatic task creation."""
        try:
            with transaction.atomic():
                serializer = self.get_serializer(data=request.data)
                if serializer.is_valid():
                    # Create customer (task will be auto-created via model's save method)
                    customer = serializer.save()
                    
                    # Ensure task was created
                    task_created = customer.tasks.exists()
                    primary_task = customer.primary_task
                    
                    return Response({
                        'success': True,
                        'message': 'Walk-in customer created successfully with automatic task',
                        'data': serializer.data,
                        'task_created': task_created,
                        'task_id': primary_task.id if primary_task else None,
                        'task_status': primary_task.status if primary_task else None
                    }, status=status.HTTP_201_CREATED)
                
                return Response({
                    'success': False,
                    'message': 'Walk-in customer creation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while creating walk-in customer',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WalkInCustomerListView(generics.ListAPIView):
    """List walk-in customers with enhanced filtering and task information."""
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
            queryset = WalkInCustomer.objects.filter(
                location=staff_profile.location
            ).select_related('location', 'location_service', 'assigned_staff', 'created_by')
        else:
            queryset = WalkInCustomer.objects.filter(
                location__tenant=staff_profile.tenant
            ).select_related('location', 'location_service', 'assigned_staff', 'created_by')
        
        # Additional filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        today_only = self.request.query_params.get('today_only')
        if today_only == 'true':
            from django.utils import timezone
            today = timezone.now().date()
            queryset = queryset.filter(arrived_at__date=today)
        
        # Filter by assigned staff
        assigned_staff_filter = self.request.query_params.get('assigned_staff')
        if assigned_staff_filter:
            queryset = queryset.filter(assigned_staff_id=assigned_staff_filter)
        
        # Filter by payment status
        payment_status_filter = self.request.query_params.get('payment_status')
        if payment_status_filter:
            queryset = queryset.filter(payment_status=payment_status_filter)
        
        return queryset.order_by('-arrived_at')
    
    def list(self, request, *args, **kwargs):
        """Handle walk-in customer listing with enhanced response and statistics."""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            # Calculate statistics
            total_customers = queryset.count()
            waiting_customers = queryset.filter(status='waiting').count()
            in_service_customers = queryset.filter(status='in_service').count()
            completed_customers = queryset.filter(status='completed').count()
            
            # Task statistics
            customers_with_tasks = sum(1 for customer in queryset if customer.tasks.exists())
            
            # Today's statistics
            from django.utils import timezone
            today = timezone.now().date()
            today_customers = queryset.filter(arrived_at__date=today).count()
            
            return Response({
                'success': True,
                'message': 'Walk-in customers retrieved successfully',
                'data': serializer.data,
                'statistics': {
                    'total_customers': total_customers,
                    'waiting_customers': waiting_customers,
                    'in_service_customers': in_service_customers,
                    'completed_customers': completed_customers,
                    'customers_with_tasks': customers_with_tasks,
                    'today_customers': today_customers
                },
                'filters_applied': {
                    'status': request.query_params.get('status'),
                    'today_only': request.query_params.get('today_only'),
                    'assigned_staff': request.query_params.get('assigned_staff'),
                    'payment_status': request.query_params.get('payment_status')
                }
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while retrieving walk-in customers',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WalkInCustomerDetailView(generics.RetrieveAPIView):
    """Retrieve detailed walk-in customer information with task details."""
    serializer_class = WalkInCustomerSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def get_queryset(self):
        """Filter queryset based on staff location/tenant."""
        try:
            staff_profile = StaffProfile.objects.get(staff=self.request.user)
            if staff_profile.location:
                return WalkInCustomer.objects.filter(
                    location=staff_profile.location
                ).select_related('location', 'location_service', 'assigned_staff', 'created_by')
            else:
                return WalkInCustomer.objects.filter(
                    location__tenant=staff_profile.tenant
                ).select_related('location', 'location_service', 'assigned_staff', 'created_by')
        except StaffProfile.DoesNotExist:
            return WalkInCustomer.objects.none()
    
    def retrieve(self, request, *args, **kwargs):
        """Handle customer detail retrieval with comprehensive information."""
        try:
            customer = self.get_object()
            serializer = self.get_serializer(customer)
            
            # Get all tasks for this customer
            tasks = customer.tasks.all().order_by('-created_at')
            task_serializer = WalkInTaskSerializer(tasks, many=True)
            
            # Get payment information
            payments = customer.payments.all().order_by('-created_at')
            payment_serializer = WalkInPaymentSerializer(payments, many=True)
            
            # Build comprehensive response
            response_data = serializer.data
            response_data['all_tasks'] = task_serializer.data
            response_data['payments'] = payment_serializer.data
            response_data['task_count'] = tasks.count()
            response_data['payment_count'] = payments.count()
            
            return Response({
                'success': True,
                'message': 'Walk-in customer details retrieved successfully',
                'data': response_data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while retrieving customer details',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WalkInCustomerUpdateView(generics.UpdateAPIView):
    """Update walk-in customer information with task synchronization."""
    serializer_class = WalkInCustomerSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def get_queryset(self):
        """Filter queryset based on staff location/tenant."""
        try:
            staff_profile = StaffProfile.objects.get(staff=self.request.user)
            if staff_profile.location:
                return WalkInCustomer.objects.filter(
                    location=staff_profile.location
                ).select_related('location', 'location_service', 'assigned_staff', 'created_by')
            else:
                return WalkInCustomer.objects.filter(
                    location__tenant=staff_profile.tenant
                ).select_related('location', 'location_service', 'assigned_staff', 'created_by')
        except StaffProfile.DoesNotExist:
            return WalkInCustomer.objects.none()
    
    def update(self, request, *args, **kwargs):
        """Handle customer update with automatic task synchronization."""
        try:
            partial = kwargs.pop('partial', True)
            customer = self.get_object()
            old_status = customer.status
            
            serializer = self.get_serializer(customer, data=request.data, partial=partial)
            
            if serializer.is_valid():
                # Update customer (serializer will handle task sync)
                updated_customer = serializer.save()
                
                # Get updated task information
                primary_task = updated_customer.primary_task
                
                # Build response with task information
                response_data = serializer.data
                if primary_task:
                    response_data['task_updated'] = True
                    response_data['task_status'] = primary_task.status
                    response_data['task_id'] = primary_task.id
                
                # Check if status changed
                new_status = updated_customer.status
                if old_status != new_status:
                    response_data['status_changed'] = {
                        'from': old_status,
                        'to': new_status,
                        'timestamp': timezone.now().isoformat()
                    }
                
                return Response({
                    'success': True,
                    'message': 'Walk-in customer updated successfully',
                    'data': response_data
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

class WalkInCustomerTaskDetailsView(generics.RetrieveAPIView):
    """Get detailed task information for a walk-in customer."""
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def get_queryset(self):
        """Filter queryset based on staff location/tenant."""
        try:
            staff_profile = StaffProfile.objects.get(staff=self.request.user)
            if staff_profile.location:
                return WalkInCustomer.objects.filter(
                    location=staff_profile.location
                ).select_related('location', 'location_service', 'assigned_staff', 'created_by')
            else:
                return WalkInCustomer.objects.filter(
                    location__tenant=staff_profile.tenant
                ).select_related('location', 'location_service', 'assigned_staff', 'created_by')
        except StaffProfile.DoesNotExist:
            return WalkInCustomer.objects.none()
    
    def get(self, request, pk=None, *args, **kwargs):
        """Get detailed task information for a customer."""
        try:
            customer = self.get_queryset().get(pk=pk)
            primary_task = customer.primary_task
            
            if primary_task:
                task_serializer = WalkInTaskSerializer(primary_task)
                
                # Get all tasks for comprehensive view
                all_tasks = customer.tasks.all().order_by('-created_at')
                all_tasks_serializer = WalkInTaskSerializer(all_tasks, many=True)
                
                return Response({
                    'success': True,
                    'message': 'Task details retrieved successfully',
                    'data': {
                        'customer_id': customer.id,
                        'customer_name': customer.name,
                        'primary_task': task_serializer.data,
                        'all_tasks': all_tasks_serializer.data,
                        'task_count': all_tasks.count()
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': 'No task found for this customer',
                    'data': {
                        'customer_id': customer.id,
                        'customer_name': customer.name,
                        'has_tasks': False
                    }
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
                'message': 'An error occurred while retrieving task details',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WalkInCustomerStartServiceView(generics.UpdateAPIView):
    """Start service for a walk-in customer (updates both customer and task)."""
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def get_queryset(self):
        """Filter queryset based on staff location/tenant."""
        try:
            staff_profile = StaffProfile.objects.get(staff=self.request.user)
            if staff_profile.location:
                return WalkInCustomer.objects.filter(
                    location=staff_profile.location
                ).select_related('location', 'location_service', 'assigned_staff', 'created_by')
            else:
                return WalkInCustomer.objects.filter(
                    location__tenant=staff_profile.tenant
                ).select_related('location', 'location_service', 'assigned_staff', 'created_by')
        except StaffProfile.DoesNotExist:
            return WalkInCustomer.objects.none()
    
    def post(self, request, pk=None, *args, **kwargs):
        """Start service for customer (updates both customer and task)."""
        try:
            customer = self.get_queryset().get(pk=pk)
            primary_task = customer.primary_task
            
            if customer.status != 'waiting':
                return Response({
                    'success': False,
                    'message': f'Customer is not in waiting status. Current status: {customer.get_status_display()}',
                    'current_status': customer.status
                }, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                # Update customer status
                customer.status = 'in_service'
                customer.service_started_at = timezone.now()
                customer.save()
                
                # Update task status
                if primary_task and primary_task.status == 'pending':
                    primary_task.status = 'in_progress'
                    primary_task.started_at = timezone.now()
                    primary_task.save()
                
                # Serialize updated customer
                serializer = WalkInCustomerSerializer(customer)
                
                return Response({
                    'success': True,
                    'message': 'Service started successfully',
                    'data': serializer.data,
                    'task_updated': primary_task is not None,
                    'task_status': primary_task.status if primary_task else None,
                    'service_started_at': customer.service_started_at.isoformat()
                }, status=status.HTTP_200_OK)
        
        except WalkInCustomer.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Walk-in customer not found',
                'error': 'Customer not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while starting service',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WalkInCustomerCompleteServiceView(generics.UpdateAPIView):
    """Complete service for a walk-in customer (updates both customer and task)."""
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def get_queryset(self):
        """Filter queryset based on staff location/tenant."""
        try:
            staff_profile = StaffProfile.objects.get(staff=self.request.user)
            if staff_profile.location:
                return WalkInCustomer.objects.filter(
                    location=staff_profile.location
                ).select_related('location', 'location_service', 'assigned_staff', 'created_by')
            else:
                return WalkInCustomer.objects.filter(
                    location__tenant=staff_profile.tenant
                ).select_related('location', 'location_service', 'assigned_staff', 'created_by')
        except StaffProfile.DoesNotExist:
            return WalkInCustomer.objects.none()
    
    def post(self, request, pk=None, *args, **kwargs):
        """Complete service for customer (updates both customer and task)."""
        try:
            customer = self.get_queryset().get(pk=pk)
            primary_task = customer.primary_task
            
            if customer.status != 'in_service':
                return Response({
                    'success': False,
                    'message': f'Customer is not in service. Current status: {customer.get_status_display()}',
                    'current_status': customer.status
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Optional completion data
            quality_rating = request.data.get('quality_rating')
            customer_feedback = request.data.get('customer_feedback')
            final_price = request.data.get('final_price')
            
            with transaction.atomic():
                # Update customer status
                customer.status = 'completed'
                customer.service_completed_at = timezone.now()
                customer.save()
                
                # Update task status
                if primary_task and primary_task.status == 'in_progress':
                    primary_task.status = 'completed'
                    primary_task.completed_at = timezone.now()
                    primary_task.progress_percentage = 100
                    
                    # Set optional completion data
                    if quality_rating:
                        primary_task.quality_rating = quality_rating
                    if customer_feedback:
                        primary_task.customer_feedback = customer_feedback
                    if final_price:
                        primary_task.final_price = final_price
                    
                    # Calculate actual duration
                    if primary_task.started_at:
                        primary_task.actual_duration = timezone.now() - primary_task.started_at
                    
                    primary_task.save()
                
                # Serialize updated customer
                serializer = WalkInCustomerSerializer(customer)
                
                return Response({
                    'success': True,
                    'message': 'Service completed successfully',
                    'data': serializer.data,
                    'task_updated': primary_task is not None,
                    'task_status': primary_task.status if primary_task else None,
                    'service_completed_at': customer.service_completed_at.isoformat(),
                    'completion_data': {
                        'quality_rating': quality_rating,
                        'customer_feedback': customer_feedback,
                        'final_price': final_price,
                        'actual_duration': primary_task.duration_formatted if primary_task else None
                    }
                }, status=status.HTTP_200_OK)
        
        except WalkInCustomer.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Walk-in customer not found',
                'error': 'Customer not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while completing service',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WalkInCustomerBulkUpdateView(generics.UpdateAPIView):
    """Bulk update multiple walk-in customers."""
    permission_classes = [IsAuthenticated]
    authentication_classes = [StaffAuthentication]
    
    def put(self, request, *args, **kwargs):
        """Handle bulk customer updates."""
        try:
            customer_ids = request.data.get('customer_ids', [])
            update_data = request.data.get('update_data', {})
            
            if not customer_ids:
                return Response({
                    'success': False,
                    'message': 'No customer IDs provided'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get staff profile
            staff_profile = StaffProfile.objects.get(staff=request.user)
            
            # Get customers accessible to this staff
            if staff_profile.location:
                customers = WalkInCustomer.objects.filter(
                    id__in=customer_ids,
                    location=staff_profile.location
                )
            else:
                customers = WalkInCustomer.objects.filter(
                    id__in=customer_ids,
                    location__tenant=staff_profile.tenant
                )
            
            if not customers.exists():
                return Response({
                    'success': False,
                    'message': 'No valid customers found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Update customers
            updated_count = 0
            updated_customers = []
            
            with transaction.atomic():
                for customer in customers:
                    for field, value in update_data.items():
                        if hasattr(customer, field):
                            setattr(customer, field, value)
                    customer.save()
                    updated_count += 1
                    updated_customers.append({
                        'id': customer.id,
                        'name': customer.name,
                        'status': customer.status
                    })
            
            return Response({
                'success': True,
                'message': f'Successfully updated {updated_count} customers',
                'updated_count': updated_count,
                'updated_customers': updated_customers
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
            'walkin_customer', 'assigned_to', 'created_by')
        
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
        ).select_related('walkin_customer', 'assigned_to', 'created_by')
    
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
            
            response_data = serializer.data
            response_data['customer_details'] = customer_serializer.data
            response_data['related_tasks'] = related_tasks_serializer.data
            
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
                      #  'amount': payment.amount,
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
                   #     'amount': payment.amount,
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

class WalkInCustomerViewSet(viewsets.ModelViewSet):
    """Enhanced ViewSet for walk-in customers with automatic task creation."""
    serializer_class = WalkInCustomerSerializer
    authentication_classes = [StaffAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on staff location/tenant."""
        try:
            staff_profile = StaffProfile.objects.get(staff=self.request.user)
            if staff_profile.location:
                return WalkInCustomer.objects.filter(
                    location=staff_profile.location
                ).select_related('location', 'location_service', 'assigned_staff', 'created_by')
            else:
                return WalkInCustomer.objects.filter(
                    location__tenant=staff_profile.tenant
                ).select_related('location', 'location_service', 'assigned_staff', 'created_by')
        except StaffProfile.DoesNotExist:
            return WalkInCustomer.objects.none()
    
    def create(self, request, *args, **kwargs):
        """Create walk-in customer with automatic task creation."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create customer (task will be auto-created)
        customer = serializer.save()
        
        # Return success response with task information
        return Response({
            'success': True,
            'message': 'Walk-in customer created successfully with automatic task',
            'data': serializer.data,
            'task_created': customer.tasks.exists(),
            'task_id': customer.primary_task.id if customer.primary_task else None
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def task_details(self, request, pk=None):
        """Get detailed task information for a customer."""
        customer = self.get_object()
        primary_task = customer.primary_task
        
        if primary_task:
            task_serializer = WalkInTaskSerializer(primary_task)
            return Response({
                'success': True,
                'data': task_serializer.data
            })
        else:
            return Response({
                'success': False,
                'message': 'No task found for this customer'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def start_service(self, request, pk=None):
        """Start service for customer (updates both customer and task)."""
        customer = self.get_object()
        primary_task = customer.primary_task
        
        if customer.status != 'waiting':
            return Response({
                'success': False,
                'message': 'Customer is not in waiting status'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update customer status
        customer.status = 'in_service'
        customer.service_started_at = timezone.now()
        customer.save()
        
        # Update task status
        if primary_task and primary_task.status == 'pending':
            primary_task.status = 'in_progress'
            primary_task.started_at = timezone.now()
            primary_task.save()
        
        return Response({
            'success': True,
            'message': 'Service started successfully',
            'data': WalkInCustomerSerializer(customer).data
        })
    
    @action(detail=True, methods=['post'])
    def complete_service(self, request, pk=None):
        """Complete service for customer (updates both customer and task)."""
        customer = self.get_object()
        primary_task = customer.primary_task
        
        if customer.status != 'in_service':
            return Response({
                'success': False,
                'message': 'Customer is not in service'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update customer status
        customer.status = 'completed'
        customer.service_completed_at = timezone.now()
        customer.save()
        
        # Update task status
        if primary_task and primary_task.status == 'in_progress':
            primary_task.status = 'completed'
            primary_task.completed_at = timezone.now()
            primary_task.progress_percentage = 100
            if primary_task.started_at:
                primary_task.actual_duration = timezone.now() - primary_task.started_at
            primary_task.save()
        
        return Response({
            'success': True,
            'message': 'Service completed successfully',
            'data': WalkInCustomerSerializer(customer).data
        })