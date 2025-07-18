from os import read
from django_mongodb_backend.expressions import value
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from .models import StaffProfile, WalkInCustomer, WalkInTask, StaffRole, WalkInPayment, WalkInTaskTemplate
from Tenant.models import Tenant, Task
from django.contrib.auth.hashers import check_password
from .models import Staff
from decimal import Decimal
from datetime import timedelta
from Location.models import Location, LocationService

# Enhanced serializer class for staff profile
class StaffProfileSerializer(serializers.ModelSerializer):
    # Enhanced read-only fields for mobile display
    full_name = serializers.SerializerMethodField(read_only=True)
    salary_formatted = serializers.SerializerMethodField(read_only=True)
    role_name = serializers.CharField(source='role.role_type', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    is_manager = serializers.SerializerMethodField(read_only=True)
    tasks_count = serializers.SerializerMethodField(read_only=True)
    active_walkins_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = StaffProfile
        fields = [
            'id', 'username', 'work_email', 'role', 'phone_number', 'email',
            'first_name', 'last_name', 'full_name', 'salary_formatted',
            'role_name', 'location_name', 'tenant_name', 'is_manager',
            'tasks_count', 'active_walkins_count', 'is_active'
        ]
        read_only_fields = ['id', 'username', 'role', 'tenant', 'location']
    
    def get_full_name(self, obj):
        """Get full name of staff member."""
        return obj.full_name
    
    def get_salary_formatted(self, obj):
        """Get formatted salary."""
        return obj.salary_formatted
    
    def get_is_manager(self, obj):
        """Check if staff is a manager."""
        return obj.role.role_type == 'manager' if obj.role else False
    
    def get_tasks_count(self, obj):
        """Get count of active tasks."""
        return Task.objects.filter(assigned_to=obj, status__in=['pending', 'in_progress']).count()
    
    def get_active_walkins_count(self, obj):
        """Get count of active walk-in customers."""
        return obj.walkin_assignments.filter(status__in=['waiting', 'in_service']).count()

# Enhanced serializer to handle staff password reset
class StaffPasswordResetSerializer(serializers.Serializer):
    """Enhanced serializer for staff password reset with better validation."""
    current_password = serializers.CharField(
        max_length=128,
        write_only=True,
        required=False,
        help_text="Current password (required for password change)",
        error_messages={
            'blank': _('Current password cannot be blank.'),
            'max_length': _('Current password cannot exceed 128 characters.')
        }
    )
    new_password = serializers.CharField(
        max_length=128,
        write_only=True,
        min_length=8,
        help_text="New password (minimum 8 characters)",
        error_messages={
            'blank': _('New password cannot be blank.'),
            'max_length': _('New password cannot exceed 128 characters.'),
            'min_length': _('New password must be at least 8 characters long.')
        }
    )
    confirm_password = serializers.CharField(
        max_length=128,
        write_only=True,
        help_text="Confirm new password",
        error_messages={
            'blank': _('Confirm password cannot be blank.'),
            'max_length': _('Confirm password cannot exceed 128 characters.')
        }
    )

    def validate(self, attrs):
        """Enhanced validation for password reset."""
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        current_password = attrs.get('current_password')

        if new_password != confirm_password:
            raise serializers.ValidationError({
                'confirm_password': _('Passwords do not match.')
            })
        
        # Validate password strength
        if len(new_password) < 8:
            raise serializers.ValidationError({
                'new_password': _('Password must be at least 8 characters long.')
            })
        
        if new_password.isdigit():
            raise serializers.ValidationError({
                'new_password': _('Password cannot be entirely numeric.')
            })

        return attrs

    def save(self, staff):
        """Save the new password for the staff member."""
        new_password = self.validated_data['new_password']
        staff.password = new_password
        staff.save()
        return staff

# Enhanced serializer class to handle staff login
class StaffLoginSerializer(serializers.Serializer):
    """Enhanced serializer for staff login with better error handling."""
    username = serializers.CharField(
        max_length=150,
        help_text="Staff username or email",
        error_messages={
            'blank': _('Username cannot be blank.'),
            'max_length': _('Username cannot exceed 150 characters.')
        }
    )
    password = serializers.CharField(
        max_length=128,
        write_only=True,
        help_text="Staff password",
        error_messages={
            'blank': _('Password cannot be blank.'),
            'max_length': _('Password cannot exceed 128 characters.')
        }
    )
    
    # Additional fields for mobile response
    remember_me = serializers.BooleanField(default=False, help_text="Keep user logged in")

    def validate(self, attrs):
        """Enhanced validation for login credentials."""
        username = attrs.get('username')
        password = attrs.get('password')

        if not username or not password:
            raise serializers.ValidationError(_('Username and password are required.'))
        
        # Try to find staff by username or email
        try:
            if '@' in username:
                staff_profile = StaffProfile.objects.get(work_email=username)
            else:
                staff_profile = StaffProfile.objects.get(username=username)
        except StaffProfile.DoesNotExist:
            raise serializers.ValidationError({
                'non_field_errors': [_('Invalid username or password.')]
            })

        # Check if staff is active
        if not staff_profile.is_active or not staff_profile.staff.is_active:
            raise serializers.ValidationError({
                'non_field_errors': [_('This account has been deactivated.')]
            })

        staff = staff_profile.staff
        # Check if the password is correct
        if not check_password(password, staff.password):
            raise serializers.ValidationError({
                'non_field_errors': [_('Invalid username or password.')]
            })

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

# Enhanced serializer to handle staff update profile
class StaffUpdateProfileSerializer(serializers.ModelSerializer):
    """Enhanced serializer for updating staff profile with mobile-friendly fields."""
    # Read-only fields for display
    staff = serializers.ReadOnlyField(source='staff.username')
    tenant = serializers.ReadOnlyField(source='tenant.name')
    location = serializers.ReadOnlyField(source='location.name')
    role = serializers.ReadOnlyField(source='role.role_type')
    salary = serializers.ReadOnlyField(source='role.salary')
    full_name = serializers.SerializerMethodField(read_only=True)
    salary_formatted = serializers.SerializerMethodField(read_only=True)
    last_updated = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = StaffProfile
        fields = [
            'id', 'staff', 'tenant', 'location', 'role', 'salary',
            'username', 'work_email', 'first_name', 'last_name',
            'phone_number', 'email', 'is_active', 'full_name',
            'salary_formatted', 'last_updated'
        ]
        read_only_fields = [
            'id', 'staff', 'tenant', 'location', 'role', 'salary',
            'username', 'work_email'
        ]

    def get_full_name(self, obj):
        return obj.full_name
    
    def get_salary_formatted(self, obj):
        return obj.salary_formatted
    
    def get_last_updated(self, obj):
        return obj.staff.updated_at.strftime("%Y-%m-%d %H:%M") if obj.staff.updated_at else None

    def validate_phone_number(self, value):
        """Validate Kenya phone number format."""
        if value and not value.startswith("+254"):
            raise serializers.ValidationError(_("Phone number must start with +254"))
        return value

    def validate(self, attrs):
        """Enhanced validation for staff profile update."""
        email = attrs.get('email')
        phone_number = attrs.get('phone_number')
        
        # Check email uniqueness
        if email and StaffProfile.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError({
                'email': _('Email is already in use.')
            })
        
        # Check phone number uniqueness
        if phone_number and StaffProfile.objects.filter(phone_number=phone_number).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError({
                'phone_number': _('Phone number is already in use.')
            })
        
        return attrs

# Enhanced task serializer for staff dashboard
class StaffTaskSerializer(serializers.Serializer):
    """Enhanced serializer for staff task statistics with mobile optimization."""
    total_tasks = serializers.IntegerField(read_only=True)
    completed_tasks = serializers.IntegerField(read_only=True)
    pending_tasks = serializers.IntegerField(read_only=True)
    in_progress_tasks = serializers.IntegerField(read_only=True)
    overdue_tasks = serializers.IntegerField(read_only=True)
    total_walkins = serializers.IntegerField(read_only=True)
    active_walkins = serializers.IntegerField(read_only=True)
    completed_walkins_today = serializers.IntegerField(read_only=True)

    def to_representation(self, instance):
        """Customize the representation with enhanced mobile data."""
        from Tenant.serializer import TaskSerializer
        from datetime import datetime
        from django.utils import timezone
        
        # Handle both staff profile instance and dictionary data
        if hasattr(instance, 'tasks'):
            # If instance is a StaffProfile, get tasks directly
            tasks = list(Task.objects.filter(assigned_to=instance))
            walkins = list(WalkInCustomer.objects.filter(assigned_staff=instance))
        else:
            # If instance is a dictionary from get_task_statistics
            tasks = instance.get('tasks', [])
            walkins = instance.get('walkins', [])
            
            # Convert QuerySets to lists if needed
            if hasattr(tasks, '__iter__') and not isinstance(tasks, list):
                tasks = list(tasks)
            if hasattr(walkins, '__iter__') and not isinstance(walkins, list):
                walkins = list(walkins)
        
        # Task statistics
        if isinstance(tasks, list) and tasks:
            total_tasks = len(tasks)
            completed_tasks = sum(1 for task in tasks if task.status == 'completed')
            pending_tasks = sum(1 for task in tasks if task.status == 'pending')
            in_progress_tasks = sum(1 for task in tasks if task.status == 'in_progress')
            overdue_tasks = sum(1 for task in tasks if task.status == 'overdue')
        else:
            total_tasks = completed_tasks = pending_tasks = in_progress_tasks = overdue_tasks = 0
            tasks = []
        
        # Walk-in statistics
        if isinstance(walkins, list) and walkins:
            total_walkins = len(walkins)
            active_walkins = sum(1 for w in walkins if w.status in ['waiting', 'in_service'])
            today = timezone.now().date()
            completed_walkins_today = sum(1 for w in walkins 
                                        if w.status == 'completed' and 
                                        w.service_completed_at and 
                                        w.service_completed_at.date() == today)
        else:
            total_walkins = active_walkins = completed_walkins_today = 0
            walkins = []

        data = {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'in_progress_tasks': in_progress_tasks,
            'overdue_tasks': overdue_tasks,
            'total_walkins': total_walkins,
            'active_walkins': active_walkins,
            'completed_walkins_today': completed_walkins_today,
        }
        
        # Serialize tasks and walkins for detailed view
        try:
            if tasks:
                data['tasks'] = TaskSerializer(tasks, many=True).data
            else:
                data['tasks'] = []
                
            if walkins:
                data['walkins'] = WalkInCustomerSerializer(walkins, many=True).data
            else:
                data['walkins'] = []
        except Exception as e:
            # Fallback if serialization fails
            data['tasks'] = []
            data['walkins'] = []
            data['serialization_error'] = str(e)
        
        return data
    
    def get_task_statistics(self, staff_profile):
        """Get enhanced task statistics including walk-ins."""
        from Tenant.models import Task
        
        # Regular tasks assigned to the staff profile (not staff user)
        tasks = Task.objects.filter(assigned_to=staff_profile).select_related(
            'booking_made', 'location', 'tenant'
        )
        
        # Walk-in customers assigned to staff profile
        walkins = WalkInCustomer.objects.filter(assigned_staff=staff_profile).select_related(
            'location', 'location_service', 'created_by'
        )
        
        return {
            'tasks': tasks,
            'walkins': walkins
        }

# Serializer to handle update of task status
class StaffUpdateTaskStatusSerializer(serializers.ModelSerializer):
    """Enhanced serializer for updating task status with better validation."""
    # Read-only fields for response
    task_name = serializers.CharField(source='description', read_only=True)  # Fixed: Task model uses 'description' not 'name'
    customer_name = serializers.CharField(source='booking_made.customer_name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    next_possible_status = serializers.SerializerMethodField(read_only=True)
    completion_time_formatted = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'status', 'task_name', 'customer_name', 'location_name',
            'next_possible_status', 'completion_time_formatted', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'assigned_to', 'tenant',
            'location', 'booking_made'
        ]
    
    def get_next_possible_status(self, obj):
        """Get next possible status transitions."""
        status_transitions = {
            'pending': ['in_progress', 'completed', 'overdue'],
            'in_progress': ['completed', 'overdue'],
            'completed': [],
            'overdue': ['in_progress', 'completed']
        }
        return status_transitions.get(obj.status, [])
    
    def get_completion_time_formatted(self, obj):
        """Get formatted completion time."""
        if hasattr(obj, 'completion_time') and obj.completion_time:
            return obj.completion_time.strftime("%Y-%m-%d %H:%M")
        return None
        
    def validate_status(self, value):
        """Enhanced validation for status transitions."""
        instance = self.instance
        if not instance:
            return value

        current_status = instance.status
        new_status = value

        valid_transitions = {
            'pending': ['in_progress', 'completed', 'overdue'],
            'in_progress': ['completed', 'overdue'],
            'completed': [],
            'overdue': ['in_progress', 'completed']
        }
        
        if current_status == new_status:
            return value

        if current_status in valid_transitions:
            if new_status in valid_transitions[current_status]:
                return value
            
            # Specific error messages
            if current_status == 'completed':
                raise serializers.ValidationError(_('Cannot change status of completed tasks.'))
            else:
                allowed = ', '.join(valid_transitions[current_status])
                raise serializers.ValidationError(
                    _(f'Invalid status transition. From "{current_status}" you can only go to: {allowed}')
                )

        return value

    def update(self, instance, validated_data):
        """Enhanced update with completion time tracking."""
        old_status = instance.status
        new_status = validated_data.get('status', instance.status)

        # Set completion time when task is completed
        if old_status != 'completed' and new_status == 'completed':
            instance.completion_time = timezone.now()
        
        instance.status = new_status
        instance.save()
        return instance

# Walk-in Customer Serializers
class WalkInCustomerSerializer(serializers.ModelSerializer):
    """Serializer for walk-in customer management."""
    # Read-only display fields
    location_name = serializers.CharField(source='location.name', read_only=True)
    service_name = serializers.CharField(source='location_service.name', read_only=True)
    service_price = serializers.CharField(source='location_service.price_formatted', read_only=True)
    assigned_staff_name = serializers.CharField(source='assigned_staff.full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    waiting_time_formatted = serializers.SerializerMethodField(read_only=True)
    service_duration_formatted = serializers.SerializerMethodField(read_only=True)
    total_amount_formatted = serializers.SerializerMethodField(read_only=True)
    arrived_at_formatted = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Task information (auto-created task details)
    primary_task_id = serializers.SerializerMethodField(read_only=True)
    primary_task_status = serializers.SerializerMethodField(read_only=True)
    primary_task_progress = serializers.SerializerMethodField(read_only=True)
    has_task = serializers.SerializerMethodField(read_only=True)
    
    # Write fields
    location_id = serializers.PrimaryKeyRelatedField(
        source='location',
        queryset=Location.objects.none(),  # Set in __init__
        required=True
    )
    location_service_id = serializers.PrimaryKeyRelatedField(
        source='location_service',
        queryset=LocationService.objects.none(),  # Set in __init__
        write_only=True,
        required=True
    )
    assigned_staff_id = serializers.PrimaryKeyRelatedField(
        source='assigned_staff',
        queryset=StaffProfile.objects.none(),  # Set in __init__
        write_only=True,
        required=False
    )

    class Meta:
        model = WalkInCustomer
        fields = [
            'id', 'name', 'phone_number', 'email', 'vehicle_plate', 'vehicle_model',
            'location_id', 'location_name', 'location_service_id', 'service_name', 'service_price',
            'assigned_staff_id', 'assigned_staff_name', 'status', 'status_display',
            'total_amount', 'total_amount_formatted', 'payment_status', 'notes',
            'arrived_at', 'arrived_at_formatted', 'service_started_at', 'service_completed_at',
            'waiting_time_formatted', 'service_duration_formatted', 'created_by_name',
            'primary_task_id', 'primary_task_status', 'primary_task_progress', 'has_task',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'arrived_at', 'service_started_at', 'service_completed_at',
            'created_at', 'updated_at'
        ]
    
    def __init__(self, *args, **kwargs):
        """Initialize with proper filtering based on staff context."""
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            # Get staff profile from request
            try:
                staff_profile = StaffProfile.objects.get(staff=request.user)
                tenant = staff_profile.tenant
                location = staff_profile.location
                
                # Filter querysets by tenant/location
                from Location.models import Location, LocationService
                
                if location:
                    self.fields['location_id'].queryset = Location.objects.filter(id=location.id)
                    self.fields['location_service_id'].queryset = LocationService.objects.filter(location=location)
                else:
                    self.fields['location_id'].queryset = Location.objects.filter(tenant=tenant)
                    self.fields['location_service_id'].queryset = LocationService.objects.filter(location__tenant=tenant)
                
                self.fields['assigned_staff_id'].queryset = StaffProfile.objects.filter(tenant=tenant, is_active=True)
                
            except (StaffProfile.DoesNotExist, AttributeError):
                from Location.models import Location, LocationService
                self.fields['location_id'].queryset = Location.objects.none()
                self.fields['location_service_id'].queryset = LocationService.objects.none()
                self.fields['assigned_staff_id'].queryset = StaffProfile.objects.none()
    
    def get_waiting_time_formatted(self, obj):
        """Get formatted waiting time."""
        waiting_time = obj.waiting_time
        if waiting_time:
            total_minutes = int(waiting_time.total_seconds() // 60)
            hours = total_minutes // 60
            minutes = total_minutes % 60
            if hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        return "0m"
    
    def get_service_duration_formatted(self, obj):
        """Get formatted service duration."""
        duration = obj.service_duration
        if duration:
            total_minutes = int(duration.total_seconds() // 60)
            hours = total_minutes // 60
            minutes = total_minutes % 60
            if hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        return None
    
    def get_total_amount_formatted(self, obj):
        """Get formatted total amount."""
        return obj.total_amount_formatted
    
    def get_arrived_at_formatted(self, obj):
        """Get formatted arrival time."""
        return obj.arrived_at.strftime("%Y-%m-%d %H:%M") if obj.arrived_at else None
    
    def get_primary_task_id(self, obj):
        """Get primary task ID."""
        primary_task = obj.primary_task
        return primary_task.id if primary_task else None
    
    def get_primary_task_status(self, obj):
        """Get primary task status."""
        primary_task = obj.primary_task
        return primary_task.status if primary_task else None
    
    def get_primary_task_progress(self, obj):
        """Get primary task progress."""
        primary_task = obj.primary_task
        return primary_task.progress_percentage if primary_task else 0
    
    def get_has_task(self, obj):
        """Check if customer has a task."""
        return obj.tasks.exists()
    
    def validate_phone_number(self, value):
        """Validate phone number format."""
        if value and not value.startswith("+254"):
            raise serializers.ValidationError(_("Phone number must start with +254"))
        return value
    
    def validate(self, data):
        """Enhanced validation for walk-in customer."""
        # Auto-set total amount from location service
        location_service = data.get('location_service')
        if location_service and not data.get('total_amount'):
            data['total_amount'] = location_service.price
        
        # Auto-set estimated duration
        if location_service and not data.get('estimated_duration'):
            data['estimated_duration'] = location_service.duration
            
        return data
    
    def create(self, validated_data):
        """Create walk-in customer with automatic task creation."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            try:
                staff_profile = StaffProfile.objects.get(staff=request.user)
                validated_data['created_by'] = staff_profile
                
                # Auto-assign to creator if no staff assigned
                if not validated_data.get('assigned_staff'):
                    validated_data['assigned_staff'] = staff_profile
                    
            except StaffProfile.DoesNotExist:
                pass
        
        # Create the customer (this will automatically create a task via the model's save method)
        instance = super().create(validated_data)
        
        # Ensure task was created (fallback)
        if not instance.tasks.exists():
            instance.create_default_task()
        
        return instance
    
    def update(self, instance, validated_data):
        """Update walk-in customer and sync with primary task."""
        old_status = instance.status
        updated_instance = super().update(instance, validated_data)
        
        # Update primary task status based on customer status
        primary_task = updated_instance.primary_task
        if primary_task:
            new_status = updated_instance.status
            
            # Sync task status with customer status
            if old_status != new_status:
                if new_status == 'in_service' and primary_task.status == 'pending':
                    primary_task.status = 'in_progress'
                    primary_task.started_at = timezone.now()
                    primary_task.save()
                elif new_status == 'completed' and primary_task.status in ['pending', 'in_progress']:
                    primary_task.status = 'completed'
                    primary_task.completed_at = timezone.now()
                    primary_task.progress_percentage = 100
                    if primary_task.started_at:
                        primary_task.actual_duration = timezone.now() - primary_task.started_at
                    primary_task.save()
        
        return updated_instance
    
    def to_representation(self, instance):
        """Enhanced representation with task information."""
        data = super().to_representation(instance)
        
        # Add comprehensive task information
        primary_task = instance.primary_task
        if primary_task:
            data['task_details'] = {
                'id': primary_task.id,
                'name': primary_task.task_name,
                'status': primary_task.status,
                'status_display': primary_task.get_status_display(),
                'progress': primary_task.progress_percentage,
                'started_at': primary_task.started_at.strftime("%Y-%m-%d %H:%M") if primary_task.started_at else None,
                'completed_at': primary_task.completed_at.strftime("%Y-%m-%d %H:%M") if primary_task.completed_at else None,
                'estimated_duration': primary_task.estimated_duration_formatted,
                'actual_duration': primary_task.duration_formatted,
                'can_start': primary_task.can_start,
                'is_overdue': primary_task.is_overdue,
            }
        else:
            data['task_details'] = None
        
        return data

# Enhanced Walk-in Task Serializer
class WalkInTaskSerializer(serializers.ModelSerializer):
    """Enhanced serializer for walk-in customer tasks with automatic assignment."""
    # Read-only display fields
    customer_name = serializers.CharField(source='walkin_customer.name', read_only=True)
    customer_vehicle = serializers.CharField(source='walkin_customer.vehicle_plate', read_only=True)
    customer_phone = serializers.CharField(source='walkin_customer.phone_number', read_only=True)
    assigned_staff_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True)
    
    # Formatted fields
    duration_formatted = serializers.SerializerMethodField(read_only=True)
    estimated_duration_formatted = serializers.SerializerMethodField(read_only=True)
    actual_duration_formatted = serializers.SerializerMethodField(read_only=True)
    final_price_formatted = serializers.SerializerMethodField(read_only=True)
    created_at_formatted = serializers.SerializerMethodField(read_only=True)
    started_at_formatted = serializers.SerializerMethodField(read_only=True)
    completed_at_formatted = serializers.SerializerMethodField(read_only=True)
    
    # Status and validation fields
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    can_start = serializers.BooleanField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = WalkInTask
        fields = [
            'id', 'walkin_customer', 'customer_name', 'customer_vehicle', 'customer_phone',
            'assigned_to', 'assigned_staff_name', 'created_by', 'created_by_name',
            'task_name', 'description', 'status', 'status_display', 'priority', 'priority_display',
            'started_at', 'started_at_formatted', 'completed_at', 'completed_at_formatted',
            'paused_at', 'estimated_duration', 'estimated_duration_formatted',
            'actual_duration', 'actual_duration_formatted', 'duration_formatted',
            'progress_percentage', 'requires_approval', 'approved_by', 'approved_by_name',
            'approved_at', 'notes', 'internal_notes', 'quality_rating', 'customer_feedback',
            'final_price', 'final_price_formatted', 'discount_applied', 'can_start', 'is_overdue',
            'created_at', 'created_at_formatted', 'updated_at'
        ]
        read_only_fields = [
            'id', 'assigned_to', 'created_by', 'started_at', 'completed_at', 'paused_at', 
            'actual_duration', 'approved_by', 'approved_at', 'created_at', 'updated_at'
        ]
    
    def get_duration_formatted(self, obj):
        """Get formatted actual duration."""
        return obj.duration_formatted
    
    def get_estimated_duration_formatted(self, obj):
        """Get formatted estimated duration."""
        return obj.estimated_duration_formatted
    
    def get_actual_duration_formatted(self, obj):
        """Get formatted actual duration."""
        return obj.duration_formatted
    
    def get_final_price_formatted(self, obj):
        """Get formatted final price."""
        return obj.final_price_formatted
    
    def get_created_at_formatted(self, obj):
        """Get formatted creation time."""
        return obj.created_at.strftime("%Y-%m-%d %H:%M") if obj.created_at else None
    
    def get_started_at_formatted(self, obj):
        """Get formatted start time."""
        return obj.started_at.strftime("%Y-%m-%d %H:%M") if obj.started_at else None
    
    def get_completed_at_formatted(self, obj):
        """Get formatted completion time."""
        return obj.completed_at.strftime("%Y-%m-%d %H:%M") if obj.completed_at else None
    
    def validate_progress_percentage(self, value):
        """Validate progress percentage."""
        if value < 0 or value > 100:
            raise serializers.ValidationError("Progress percentage must be between 0 and 100")
        return value
    
    def validate_quality_rating(self, value):
        """Validate quality rating."""
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("Quality rating must be between 1 and 5")
        return value
    
    def validate_status(self, value):
        """Validate status transitions."""
        if self.instance:
            current_status = self.instance.status
            valid_transitions = {
                'pending': ['in_progress', 'cancelled', 'on_hold'],
                'in_progress': ['completed', 'paused', 'cancelled', 'on_hold'],
                'paused': ['in_progress', 'cancelled'],
                'on_hold': ['pending', 'cancelled'],
                'completed': [],
                'cancelled': []
            }
            
            if current_status != value and value not in valid_transitions.get(current_status, []):
                allowed = ', '.join(valid_transitions.get(current_status, []))
                raise serializers.ValidationError(
                    f'Invalid status transition from "{current_status}" to "{value}". '
                    f'Allowed transitions: {allowed}'
                )
        return value
    
    def validate_walkin_customer(self, value):
        """Validate walk-in customer belongs to same tenant/location."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            try:
                staff_profile = StaffProfile.objects.get(staff=request.user)
                
                # Check if customer belongs to same location/tenant
                if staff_profile.location and value.location != staff_profile.location:
                    raise serializers.ValidationError(
                        "Cannot create task for customer from different location"
                    )
                elif value.location.tenant != staff_profile.tenant:
                    raise serializers.ValidationError(
                        "Cannot create task for customer from different tenant"
                    )
            except StaffProfile.DoesNotExist:
                raise serializers.ValidationError("Staff profile not found")
        
        return value
    
    def validate(self, data):
        """Enhanced validation for walk-in tasks."""
        # Validate that walk-in customer exists and is not completed
        walkin_customer = data.get('walkin_customer')
        if walkin_customer and walkin_customer.status == 'completed':
            raise serializers.ValidationError({
                'walkin_customer': 'Cannot create task for completed customer'
            })
        
        # Auto-set final price from customer's service if not provided
        if walkin_customer and not data.get('final_price'):
            data['final_price'] = walkin_customer.total_amount
        
        # Auto-set estimated duration from customer's service if not provided
        if walkin_customer and not data.get('estimated_duration'):
            data['estimated_duration'] = walkin_customer.estimated_duration
        
        return data
    
    def create(self, validated_data):
        """Create task with automatic assignment to logged-in staff."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            try:
                staff_profile = StaffProfile.objects.get(staff=request.user)
                
                # Automatically assign to logged-in staff
                validated_data['assigned_to'] = staff_profile
                validated_data['created_by'] = staff_profile
                
                # Set default task name if not provided
                if not validated_data.get('task_name'):
                    customer = validated_data.get('walkin_customer')
                    if customer and customer.location_service:
                        validated_data['task_name'] = f"{customer.location_service.name} - {customer.name}"
                    else:
                        validated_data['task_name'] = f"Walk-in Service - {customer.name if customer else 'Unknown'}"
                
            except StaffProfile.DoesNotExist:
                raise serializers.ValidationError("Staff profile not found")
        else:
            raise serializers.ValidationError("Authentication required")
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update task with proper timing and status handling."""
        old_status = instance.status
        new_status = validated_data.get('status', instance.status)
        
        # Handle status-based timing
        if old_status == 'pending' and new_status == 'in_progress':
            instance.started_at = timezone.now()
            # Update customer status
            if instance.walkin_customer.status == 'waiting':
                instance.walkin_customer.status = 'in_service'
                instance.walkin_customer.service_started_at = timezone.now()
                instance.walkin_customer.save()
                
        elif old_status == 'in_progress' and new_status == 'completed':
            instance.completed_at = timezone.now()
            instance.progress_percentage = 100
            
            # Calculate actual duration
            if instance.started_at:
                instance.actual_duration = timezone.now() - instance.started_at
            
            # Update customer status
            instance.walkin_customer.status = 'completed'
            instance.walkin_customer.service_completed_at = timezone.now()
            instance.walkin_customer.save()
            
        elif old_status == 'in_progress' and new_status == 'paused':
            instance.paused_at = timezone.now()
        
        return super().update(instance, validated_data)

# Task Template Serializer
class WalkInTaskTemplateSerializer(serializers.ModelSerializer):
    """Serializer for walk-in task templates."""
    estimated_duration_formatted = serializers.SerializerMethodField(read_only=True)
    default_price_formatted = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = WalkInTaskTemplate
        fields = [
            'id', 'name', 'description', 'estimated_duration', 'estimated_duration_formatted',
            'service_items', 'default_price', 'default_price_formatted', 'requires_approval',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_estimated_duration_formatted(self, obj):
        """Get formatted estimated duration."""
        if obj.estimated_duration:
            total_seconds = int(obj.estimated_duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            if hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        return None
    
    def get_default_price_formatted(self, obj):
        """Get formatted default price."""
        return f"KSh {obj.default_price:,.2f}" if obj.default_price else "KSh 0.00"

# Task Status Update Serializer
class WalkInTaskStatusSerializer(serializers.Serializer):
    """Serializer for updating task status only."""
    status = serializers.ChoiceField(choices=WalkInTask.TASK_STATUS_CHOICES)
    progress_percentage = serializers.IntegerField(min_value=0, max_value=100, required=False)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    quality_rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    customer_feedback = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    
    
    
    # Walk-in Payment Serializers
class WalkInPaymentSerializer(serializers.ModelSerializer):
        """Serializer for walk-in customer payments."""
        # Read-only display fields
        customer_name = serializers.CharField(source='walkin_customer.name', read_only=True)
        customer_vehicle = serializers.CharField(source='walkin_customer.vehicle_plate', read_only=True)
        amount_formatted = serializers.SerializerMethodField(read_only=True)
        processed_by_name = serializers.CharField(source='processed_by.full_name', read_only=True)
        status_display = serializers.CharField(source='get_status_display', read_only=True)
        payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
        created_at_formatted = serializers.SerializerMethodField(read_only=True)
        completed_at_formatted = serializers.SerializerMethodField(read_only=True)
        
        class Meta:
            model = WalkInPayment
            fields = [
                'id', 'walkin_customer', 'customer_name', 'customer_vehicle',
                'amount', 'amount_formatted', 'payment_method', 'payment_method_display',
                'payment_reference', 'status', 'status_display', 'phone_number',
                'checkout_request_id', 'merchant_request_id', 'transaction_id',
                'failure_reason', 'notes', 'processed_by', 'processed_by_name',
                'created_at', 'created_at_formatted', 'completed_at', 'completed_at_formatted',
                'updated_at', 'is_successful', 'is_pending'
            ]
            read_only_fields = [
                'id', 'payment_reference', 'checkout_request_id', 'merchant_request_id',
                'transaction_id', 'created_at', 'completed_at', 'updated_at'
            ]
        
        def get_amount_formatted(self, obj):
            """Get formatted amount."""
            return obj.amount_formatted
        
        def get_created_at_formatted(self, obj):
            """Get formatted creation time."""
            return obj.created_at.strftime("%Y-%m-%d %H:%M") if obj.created_at else None
        
        def get_completed_at_formatted(self, obj):
            """Get formatted completion time."""
            return obj.completed_at.strftime("%Y-%m-%d %H:%M") if obj.completed_at else None
    
class MpesaPaymentInitiateSerializer(serializers.Serializer):
        """Serializer for initiating M-Pesa payments for walk-in customers."""
        walkin_customer_id = serializers.IntegerField(help_text="Walk-in customer ID")
        phone_number = serializers.CharField(
            max_length=20,
            help_text="Customer's phone number in format +254XXXXXXXXX"
        )
        amount = serializers.DecimalField(
            max_digits=10,
            decimal_places=2,
            help_text="Payment amount"
        )
        description = serializers.CharField(
            max_length=200,
            default="Walk-in Car Wash Service",
            help_text="Payment description"
        )
        
        def validate_phone_number(self, value):
            """Validate phone number format."""
            from Staff.payment_gateways.walkin_mpesa import WalkInMpesaService
            
            try:
                service = WalkInMpesaService()
                sanitized = service.sanitize_phone_number(value)
                return sanitized
            except ValueError as e:
                raise serializers.ValidationError(str(e))
        
        def validate_walkin_customer_id(self, value):
            """Validate that walk-in customer exists and can accept payments."""
            try:
                customer = WalkInCustomer.objects.get(id=value)
                if customer.payment_status == 'paid':
                    raise serializers.ValidationError("Payment already completed for this customer")
                return value
            except WalkInCustomer.DoesNotExist:
                raise serializers.ValidationError("Walk-in customer not found")
    
class PaymentStatusSerializer(serializers.Serializer):
        """Serializer for payment status responses."""
        success = serializers.BooleanField()
        payment_status = serializers.CharField()
        message = serializers.CharField()
        transaction_id = serializers.CharField(required=False)
        amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
