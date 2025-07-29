from django.contrib import admin
from Tenant.models import TenantProfile,Tenant, Task
from booking.models import booking
from Staff.models import StaffProfile,StaffRole
from Location.models import Location, Service, LocationService
from Staff.models import StaffProfile, StaffRole, Staff, WalkInCustomer, WalkInTask, WalkInPayment

from .models import CustomerProfile, AuditLog
from Tenant.models import CarCheckIn
from Report_Analysis.models import  (
    ReportTemplate, GeneratedReport, ReportSchedule, AnalyticsSnapshot,
    CustomReportFilter, ReportBookmark, LocationPerformanceMetrics,
    TenantAnalyticsSummary
)
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponse


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
        return True
    def has_change_permission(self, request, obj=None):
        """
        Disable the change permission for Location.
        """
        return True
    def has_delete_permission(self, request, obj=None):
        """
        Disable the delete permission for Location.
        """
        return True
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
    
    
@admin.register(WalkInCustomer)
class WalkInCustomerAdmin(admin.ModelAdmin):
    """
    Admin interface for WalkInCustomer model.
    """
    list_display = ('name', 'location', 'id', 'email', 'created_at')
    search_fields = ('name', 'phone_number', 'email')
    
    def has_add_permission(self, request):
        """
        Disable the add permission for WalkInCustomer.
        """
        return True
    
    def has_change_permission(self, request, obj=None):
        """
        Disable the change permission for WalkInCustomer.
        """
        return True
    
    def has_delete_permission(self, request, obj=None):
        """
        Disable the delete permission for WalkInCustomer.
        """
        return True
    
@admin.register(WalkInTask)
class WalkInTaskAdmin(admin.ModelAdmin):
    """
    Admin interface for WalkInTask model.
    """
    list_display = ('walkin_customer', 'assigned_to', 'status', 'task_name')
    search_fields = ('status','task_name')
    list_filter = ('status', 'assigned_to')

    def has_add_permission(self, request):
        """
        Disable the add permission for WalkInTask.
        """
        return True

    def has_change_permission(self, request, obj=None):
        """
        Disable the change permission for WalkInTask.
        """
        return True

    def has_delete_permission(self, request, obj=None):
        """
        Disable the delete permission for WalkInTask.
        """
        return True
    
@admin.register(WalkInPayment)
class WalkInPaymentAdmin(admin.ModelAdmin):
    """
    Admin interface for WalkInPayment model.
    """
    list_display = ('walkin_customer', 'amount_formatted', 'payment_method', 'status', 'created_at')
    list_filter = ('payment_method', 'status', 'created_at')
    search_fields = ('walkin_customer__name', 'payment_reference', 'transaction_id')
    readonly_fields = ('payment_reference', 'checkout_request_id', 'merchant_request_id', 'transaction_id')
    
    def amount_formatted(self, obj):
        """Display formatted amount."""
        return obj.amount_formatted
    amount_formatted.short_description = 'Amount'
    
    def has_add_permission(self, request):
        """Disable the add permission for WalkInPayment."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Enable limited change permission for WalkInPayment."""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Disable the delete permission for WalkInPayment."""
        return False




@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'report_type', 'frequency', 'is_active', 'auto_generate', 'created_at']
    list_filter = ['report_type', 'frequency', 'is_active', 'auto_generate', 'created_at']
    search_fields = ['name', 'tenant__name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'tenant', 'report_type', 'description')
        }),
        ('Configuration', {
            'fields': ('frequency', 'is_active', 'auto_generate', 'email_recipients', 'config')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(GeneratedReport)
class GeneratedReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'report_type', 'status', 'format', 'download_link', 'created_at', 'expires_at']
    list_filter = ['report_type', 'status', 'format', 'created_at']
    search_fields = ['name', 'tenant__name']
    readonly_fields = ['id', 'created_at', 'download_link', 'is_expired_display']
    
    def download_link(self, obj):
        if obj.file_url:
            return format_html('<a href="{}" target="_blank">Download</a>', obj.file_url)
        return "No file"
    download_link.short_description = "Download"
    
    def is_expired_display(self, obj):
        return "Yes" if obj.is_expired() else "No"
    is_expired_display.short_description = "Is Expired"
    is_expired_display.boolean = True

@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = ['template', 'tenant', 'is_active', 'next_run', 'last_run', 'run_count']
    list_filter = ['is_active', 'next_run', 'created_at']
    search_fields = ['template__name', 'tenant__name']

@admin.register(AnalyticsSnapshot)
class AnalyticsSnapshotAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'location', 'snapshot_date', 'total_bookings', 'daily_revenue', 'completion_rate']
    list_filter = ['snapshot_date', 'tenant', 'location']
    search_fields = ['tenant__name', 'location__name']
    readonly_fields = ['completion_rate']
    
    def completion_rate(self, obj):
        if obj.total_bookings > 0:
            return f"{(obj.completed_bookings / obj.total_bookings * 100):.1f}%"
        return "0%"
    completion_rate.short_description = "Completion Rate"

@admin.register(LocationPerformanceMetrics)
class LocationPerformanceMetricsAdmin(admin.ModelAdmin):
    list_display = ['location', 'date', 'bookings_received', 'gross_revenue', 'staff_utilization_rate']
    list_filter = ['date', 'location__tenant', 'location']
    search_fields = ['location__name', 'location__tenant__name']

@admin.register(TenantAnalyticsSummary)
class TenantAnalyticsSummaryAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'period_type', 'period_start', 'period_end', 'total_revenue', 'completion_rate']
    list_filter = ['period_type', 'period_start', 'tenant']
    search_fields = ['tenant__name']

@admin.register(CustomReportFilter)
class CustomReportFilterAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'filter_type', 'is_default', 'created_at']
    list_filter = ['filter_type', 'is_default', 'created_at']
    search_fields = ['name', 'tenant__name']

@admin.register(ReportBookmark)
class ReportBookmarkAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'is_favorite', 'access_count', 'last_accessed', 'created_by']
    list_filter = ['is_favorite', 'last_accessed', 'created_at']
    search_fields = ['name', 'tenant__name']