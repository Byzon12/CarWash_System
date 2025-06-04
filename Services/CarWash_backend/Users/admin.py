
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
    list_display =( 'user', 'action', 'timestamp', 'success', 'ip_address', 'user_agent', 'details')
    readonly_fields = ('user', 'action', 'timestamp', 'success', 'ip_address', 'user_agent', 'details') 
    search_fields = ('user__username', 'action')
    list_filter = ('action', 'success', 'timestamp')
    
    def has_add_permission(self, request):
        return False