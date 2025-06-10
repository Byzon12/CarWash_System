
from django.contrib import admin
from Tenant.models import EmployeeRole, TenantProfile,Tenant, Employee,EmployeeRole


from .models import CustomerProfile, AuditLog

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
    list_display = ('name', 'contact_email', 'contact_phone', 'created_at', 'updated_at')
    search_fields = ('name', 'contact_email', 'contact_phone')
    list_filter = ('created_at', 'updated_at')
    
    
  #tenant profile admin  
    
@admin.register(TenantProfile)
class TenantProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for TenantProfile model.
    """
    list_display = ('tenant','business_name', 'phone_number', 'created_at', 'updated_at', 'logo')
    search_fields = ('business_name', 'email', 'phone_number')
    list_filter = ('created_at', 'updated_at')
    
    def has_add_permission(self, request):
        """
        Disable the add permission for TenantProfile.
        """
        return False


#employee admin

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    """Admin interface for employee model. """
    list_display = ('tenant', 'id','full_name', 'work_email', 'phone_number', 'role_type', 'get_role_salary', 'created_at', 'updated_at')
    search_fields = ('tenant__name', 'full_name', 'work_email', 'phone_number')

#custom method to get role salary for admin display
    def get_role_salary(self, obj):
        if obj.role:
            return obj.role.salary_role
        return None
    get_role_salary.short_description = 'Role Salary'
    def has_add_permission(self, request):
        """
        Disable the add permission for Employee.
        """
        return True

    #admin site to register employee salary and roles
@admin.register(EmployeeRole)
class EmployeeRoleAdmin(admin.ModelAdmin):
    """
    Admin interface for EmployeeRole model.
    """
    list_display = ('role_type', 'description', 'salary')
    list_filter = ('role_type',)
    search_fields = ('role_type',)

    def has_add_permission(self, request):
        """
        Disable the add permission for EmployeeRole.
        """
        return True