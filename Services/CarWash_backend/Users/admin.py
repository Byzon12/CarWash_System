
from django.contrib import admin


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