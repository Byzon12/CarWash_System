
from os import read
from django_mongodb_backend.expressions import value
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from .models import StaffProfile
from Tenant.models import Tenant, Task
from  django.contrib.auth.hashers import check_password
from .models import Staff





#serializer class for staff profile
class StaffProfileSerializer(serializers.ModelSerializer):
  

    class Meta:
        model = StaffProfile
        fields = ['username', 'work_email', 'role', 'phone_number', 'email']
        
        
#serializer to handle staff password reset
class StaffPasswordResetSerializer(serializers.Serializer):
    """
    Serializer for staff password reset.
    This serializer is used to validate the new password for a staff member.
    It includes fields for the new password and confirms that the new password matches.
    """
    new_password = serializers.CharField(
        max_length=128,
        write_only=True,
        error_messages={
            'blank': _('New password cannot be blank.'),
            'max_length': _('New password cannot exceed 128 characters.')
        }
    )
    confirm_password = serializers.CharField(
        max_length=128,
        write_only=True,
        error_messages={
            'blank': _('Confirm password cannot be blank.'),
            'max_length': _('Confirm password cannot exceed 128 characters.')
        }
    )

    def validate(self, attrs):
        """
        Validate the new password and confirm password.
        """
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')

        if new_password != confirm_password:
            raise serializers.ValidationError(_('Passwords do not match.'))

        return attrs
    def save(self, staff):
        """
        Save the new password for the staff member.
        This method hashes the new password and updates the staff member's password.
        """
        new_password = self.validated_data['new_password']
        #hash the password before saving
        staff.password = new_password
        staff.save()
        return staff

        

# serializer class to handle staff login  using details from employee model
class StaffLoginSerializer(serializers.Serializer):
    """
    Serializer for staff login.
    This serializer is used to validate the login credentials of a staff member.
    It includes fields for username and password, and it validates that the user exists.
    """
    username = serializers.CharField(
        max_length=150,
        error_messages={
            'blank': _('Username cannot be blank.'),
            'max_length': _('Username cannot exceed 150 characters.')
        }
    )
    password = serializers.CharField(
        max_length=128,
        write_only=True,
        error_messages={
            'blank': _('Password cannot be blank.'),
            'max_length': _('Password cannot exceed 128 characters.')
        }
    )

        
    def validate(self, attrs):
        """
        Validate the login credentials.
        This method checks if the user exists and if the password is correct.
        """
        username = attrs.get('username')
        password = attrs.get('password')

       #check if username and password are provided
        if not username or not password:
            raise serializers.ValidationError(_('Username and password are required.'))
        
        try:
            staff_profile = StaffProfile.objects.get(username=username)
        except StaffProfile.DoesNotExist:
            raise serializers.ValidationError(_('Invalid username or password.'))

        staff = staff_profile.staff
        # Check if the password is correct
        if not check_password(password, staff.password):
            raise serializers.ValidationError(_('Invalid username or password.'))
        #store for later use

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
    
#serializer to handle staff update profile
class StaffUpdateProfileSerializer(serializers.ModelSerializer):
    """Serializer for updating staff profile.
This serializer is used to update the profile of a staff member. and get the staff profile details.
It includes fields for email, phone number, work email, first name, and last name.  """
#read only fields
    staff = serializers.ReadOnlyField(source='staff.username')
    tenant = serializers.ReadOnlyField(source='tenant.name')
    location = serializers.ReadOnlyField(source='location.name')
    role = serializers.ReadOnlyField(source='role.role_type')
    salary = serializers.ReadOnlyField(source='role.salary')
    class Meta:
        model = StaffProfile
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'username', 'role', 'tenant', 'location',]

    def validate(self, attrs):
        # Validate the staff profile update.
        #check if the email is already in use by another staff member
        #during the check dont include the current staff member's email
        email = attrs.get('email')
        if email and StaffProfile.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError(_('Email is already in use.'))
        
        #check if the phone number is already in use by another staff member
        #during the check dont include the current staff member's phone number
        
        phone_number = attrs.get('phone_number')
        if phone_number and StaffProfile.objects.filter(phone_number=phone_number).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError(_('Phone number is already in use.')) 
        
        return attrs
    
    #override the update methodto update the staff member's profile
    def update(self, instance, validated_data):
        # Update the staff profile fields
        instance.email = validated_data.get('email', instance.email)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.work_email = validated_data.get('work_email', instance.work_email)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.save()
        return instance
    

#task serializer for staff dashboard
class StaffTaskSerializer(serializers.Serializer):
    """
    StaffTaskSerializer is a custom serializer for aggregating and presenting staff task data on the staff dashboard.
    This serializer provides:
    - The total number of tasks assigned to an individual staff member.
    - The count of tasks based on their status: completed, pending, and overdue.
    - A detailed list of tasks, serialized using the TaskSerializer.
    Fields:
    
    total_tasks (int): Total number of tasks assigned to the staff member.
    completed_tasks (int): Number of tasks marked as completed.
    pending_tasks (int): Number of tasks that are still pending.
    overdue_tasks (int): Number of tasks that are overdue.
Methods:
    to_representation(instance): Customizes the serialized output, including task counts and a detailed list of tasks.
   

    this serializer is used to serialize the task data for the staff dashboard.
    count number of task assigned to individual staff,
    count the task base on status of the task,
    and return the task details.
    
    """
    
    total_tasks = serializers.IntegerField(read_only=True)
    completed_tasks = serializers.IntegerField(read_only=True)
    pending_tasks = serializers.IntegerField(read_only=True)
    in_progress_tasks = serializers.IntegerField(read_only=True)
    overdue_tasks = serializers.IntegerField(read_only=True)
   

    def to_representation(self, instance):
        """
        Customize the representation of the serialized data.
        """
        from Tenant.serializer import TaskSerializer
        from datetime import datetime
        from django.utils import timezone
        
        tasks = instance.get('tasks', [])
        # Ensure tasks is a list, if not, initialize it as an empty list
        if not isinstance(tasks, list):
            #initialize counters
            total_tasks = len(tasks)
            completed_tasks = sum(1 for task in tasks if task.status == 'completed')
            pending_tasks = sum(1 for task in tasks if task.status == 'pending')
            in_progress_tasks = sum(1 for task in tasks if task.status == 'in_progress')
            overdue_tasks = sum(1 for task in tasks if task.status == 'overdue')
            tasks = []
        else:
            # Count the number of tasks assigned to the staff member
            total_tasks = len(tasks)
            # Count the number of completed tasks
            completed_tasks = sum(1 for task in tasks if task.status == 'completed')
            # Count the number of in-progress tasks
            in_progress_tasks = sum(1 for task in tasks if task.status == 'in_progress')
            # Count the number of pending tasks
            pending_tasks = sum(1 for task in tasks if task.status == 'pending')
            # Count the number of overdue tasks
            overdue_tasks = sum(1 for task in tasks if task.status == 'overdue' and task.due_date < timezone.now())
#response data to be returned
        data = {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'in_progress_tasks': in_progress_tasks,
            'overdue_tasks': overdue_tasks,
        }
        #dynamically serialize the tasks
       
        if tasks:
            data['tasks'] = TaskSerializer(tasks, many=True).data
        else:
            data['tasks'] = []
        return data
    
    #get task statistics for the staff member
    def get_task_statistics(self, staff):
        """
        Get the task statistics for a specific staff member.
        This method retrieves the tasks assigned to the staff member and aggregates the statistics.
        """
        from Tenant.models import Task
        # Retrieve tasks assigned to the staff member
        tasks = Task.objects.filter(assigned_to=staff)
        
        # Aggregate task statistics
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(status='completed').count()
        pending_tasks = tasks.filter(status='pending').count()
        in_progress_tasks = tasks.filter(status='in_progress').count()
        overdue_tasks = tasks.filter(status='overdue', due_date__lt=timezone.now()).count()
        
        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'in_progress_tasks': in_progress_tasks,
            'overdue_tasks': overdue_tasks,
            'tasks': tasks
        }
    
#serializer to handle upadte of task status
class StaffUpdateTaskStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for updating the status of a task assigned to a staff member.
    This serializer is used to validate and update the status of a task.
    the task status can be updated to one of the following choices:
    - pending
    - in_progress
    - completed
    - overdue
    """
    class Meta:
        model = Task
        fields = ['status']
        read_only_fields = ['id', 'created_at', 'updated_at', 'assigned_to', 'tenant', 'location', 'booking_made']
        
    def validate_status(self, value):
        """validate the status of the task according to transition flow
        pending -> in_progress
        in_progress -> completed
        """
        instance = self.instance
        if not instance:
            return value

        current_status = instance.status
        new_status = value

        valid_transitions = {
            'pending': ['in_progress', 'completed', 'overdue'],
            'in_progress': ['completed', 'overdue'],
            'completed': [],  # no further transitions allowed
            'overdue': ['in_progress']  # can be moved back to in_progress
        }
        
        #if status is the same, allow it (no change)
        if current_status == new_status:
            return value

        # check if the transition is allowed
        if current_status in valid_transitions:
            if new_status in valid_transitions[current_status]:
                return value
            # disallow invalid transitions
            if current_status == 'pending' and new_status == 'completed':
                raise serializers.ValidationError(_('Cannot directly complete a pending task.'))
            elif current_status == 'completed':
                raise serializers.ValidationError(_('No further transitions allowed for completed tasks.'))
            # if not a valid transition, raise error
            raise serializers.ValidationError(_(f'Cannot transition from {current_status} to {new_status}.'))

        return value

    def update(self, instance, validated_data):
            """
            Update the task status and return the updated instance.
            """
            old_status = instance.status
            new_status = validated_data.get('status', instance.status)

            #complitation time status
            if old_status == 'in_progress' and new_status == 'completed':
                instance.completion_time = timezone.now()

        
            instance.save()
            return instance