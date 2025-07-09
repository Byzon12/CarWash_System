
from django.contrib import admin
from Tenant.models import TenantProfile,Tenant, Task
from booking.models import booking
from Staff.models import StaffProfile,StaffRole
from Location.models import Location, Service, LocationService
from Staff.models import StaffProfile, StaffRole,Staff

from .models import CustomerProfile, AuditLog
from Tenant.models import CarCheckIn

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for CustomerProfile model.
    """
    list_display = ('user', 'phone_number', 'address', 'loyalty_points', 'updated_at')
   # search_fields = ('user__username', 'phone_number', 'address')
    list_filter = ('updated_at',)
    
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        """
        Disable the change permission for CustomerProfile.
        """
        return False
    
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Admin interface for AuditLog model.
    """
    list_display =('get_user','get_action', 'timestamp', 'success', 'ip_address', 'user_agent', 'details')
   
    
    @admin.display(description='User')  
    def get_user(self, obj):
        """
        Display the username in the admin interface.
        """
        return obj.user if obj.user else 'Anonymous'
    @admin.display(description='Action')
    def get_action(self, obj):
        """
        Display the action in the admin interface.
        """
        return obj.action.replace('_', ' ').capitalize() if obj.action else 'N/A'
    
#registering tenant 
@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    """
    Admin interface for Tenant model.
    """
    list_display = ('name', 'id', 'contact_email', 'contact_phone', 'created_at', 'updated_at')
    search_fields = ('name', 'contact_email', 'contact_phone')
    list_filter = ('created_at', 'updated_at')
    
    
  #tenant profile admin  
    
@admin.register(TenantProfile)
class TenantProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for TenantProfile model.
    """
    list_display = ('tenant','business_name', 'phone_number', 'created_at', 'updated_at','image_tag')
    search_fields = ('business_name', 'email', 'phone_number')
    list_filter = ('created_at', 'updated_at')
    
    def has_add_permission(self, request):
        """
        Disable the add permission for TenantProfile.
        """
        return False
    def has_change_permission(self, request, obj = ...):
        """Disable the change permission for TenantProfile. """
        return  False
    def has_delete_permission(self, request, obj = ...):
        """Disable the delete permission for TenantProfile. """
        return   False


#employee admin


    
    
# Registering Location model in the admin interface
@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    """
    Admin interface for Location model.
    """
    list_display = ('name', 'address', 'contact_number', 'email', 'id')
    search_fields = ('name', 'address', 'contact_number', 'email')
    list_filter = ('created_at', 'updated_at')
    def has_add_permission(self, request):
        """
        Disable the add permission for Location.
        """
        return False
    def has_change_permission(self, request, obj=None):
        """
        Disable the change permission for Location.
        """
        return False
    def has_delete_permission(self, request, obj=None):
        """
        Disable the delete permission for Location.
        """
        return False
# Registering services in the admin interface

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    """
    Admin interface for Service model.
    """
    list_display = ('name', 'description','id', 'tenant')
    
    

    def has_add_permission(self, request):
        """
        Disable the add permission for Service.
        """
        return False

    def has_change_permission(self, request, obj=None):
        """
        Disable the change permission for Service.
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """
        Disable the delete permission for Service.
        """
        return False

# Registering packages in the admin interface
@admin.register(LocationService)
class LocationServiceAdmin(admin.ModelAdmin):
    """
    Admin interface for LocationService model.
    """
    list_display = ('location', 'name', 'price', 'duration', 'description', 'id')

    def has_add_permission(self, request):
        """
        Disable the add permission for LocationService.
        """
        return False

    def has_change_permission(self, request, obj=None):
        """
        Disable the change permission for LocationService.
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """
        Disable the delete permission for Package.
        """
        return False

# Registering Booking model in the admin interface
@admin.register(booking)
class BookingAdmin(admin.ModelAdmin):
    """
    Admin interface for Booking model.
    """
    list_display = ('location', 'customer', 'booking_date', 'status', 'payment_status','id', 'updated_at')
    search_fields = ('customer','status')
    list_filter = ('status', 'payment_status', 'created_at')
    
    def has_add_permission(self, request):
        """
        Disable the add permission for Booking.
        """
        return False
    def has_change_permission(self, request, obj=None):
        """
        Disable the change permission for Booking.
        """
        return True
    def has_delete_permission(self, request, obj=None):
        """
        Disable the delete permission for Booking.
        """
        return False
    
    #registering Staff
@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    """
    Admin interface for Staff model.
    """
    list_display = ('email', 'tenant')
    search_fields = ('email', 'phone_number')
    list_filter = ('tenant',)

    def has_add_permission(self, request):
        """
        Disable the add permission for Staff.
        """
        return False
    
# registering admin site for staff profile
@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for StaffProfile model.
    """
    list_display = ('username', 'work_email', 'id', 'phone_number', 'role', 'get_role_salary')
    search_fields = ('work_email', 'phone_number')

#custom method to get role salary for admin display
    def get_role_salary(self, obj):
        if obj.role:
            return obj.role.salary
        return None
    get_role_salary.short_description = 'Salary'
    def has_add_permission(self, request):
        """
        Disable the add permission for Employee.
        """
        return False
    def has_change_permission(self, request, obj=None):
        """
        Disable the change permission for Employee.
        """
        return False
    def has_delete_permission(self, request, obj=None):
        """
        Disable the delete permission for Employee.
        """
        return False

    def has_add_permission(self, request):
        """
        Disable the add permission for StaffProfile.
        """
        return True
    def has_change_permission(self, request, obj=None):
        """
        Disable the change permission for StaffProfile.
        """
        return True

    def has_delete_permission(self, request, obj=None):
        """
        Disable the delete permission for StaffProfile.
        """
        return True
    
# Registering StaffRole model in the admin interface
@admin.register(StaffRole)
class StaffRoleAdmin(admin.ModelAdmin):
    """
    Admin interface for StaffRole model.
    """
    list_display = ('id', 'role_type', 'description', 'salary')
    list_filter = ('role_type',)
    search_fields = ('role_type',)

    def has_add_permission(self, request):
        """
        Disable the add permission for StaffRole.
        """
        return True

    def has_change_permission(self, request, obj=None):
        """
        Disable the change permission for StaffRole.
        """
        return True

    def has_delete_permission(self, request, obj=None):
        """
        Disable the delete permission for StaffRole.
        """
        return True


#registering Task model in the admin interface
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """
    Admin interface for Task model.
    """
    list_display = ('booking_made', 'location', 'due_date', 'assigned_to', 'status', 'tenant','task_id')
    search_fields = ('due_date', 'description', 'assigned_to__full_name')
    list_filter = ('status', 'due_date')

    def has_add_permission(self, request):
        """
        Disable the add permission for Task.
        """
        return True

    def has_change_permission(self, request, obj=None):
        """
        Disable the change permission for Task.
        """
        return True

    def has_delete_permission(self, request, obj=None):
        """
        Disable the delete permission for Task.
        """
        return True
    
    

# Registering CarCheckIn model in the admin interface
@admin.register(CarCheckIn)
class CarCheckInAdmin(admin.ModelAdmin):
    """
    Admin interface for CarCheckIn model.
    """
    list_display = ('car_plate_number', 'task', 'checkout_time')
    search_fields = ('car_plate_number',)

    def has_add_permission(self, request):
        """
        Disable the add permission for CarCheckIn.
        """
        return True

    def has_change_permission(self, request, obj=None):
        """
        Disable the change permission for CarCheckIn.
        """
        return True

    def has_delete_permission(self, request, obj=None):
        """
        Disable the delete permission for CarCheckIn.
        """
        return True