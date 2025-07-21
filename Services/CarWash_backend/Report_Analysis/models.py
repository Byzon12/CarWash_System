from django.db import models
from django.utils import timezone
from decimal import Decimal
from Tenant.models import Tenant
from Location.models import Location
from Staff.models import StaffProfile
import uuid

class ReportTemplate(models.Model):
    """Templates for different types of reports"""
    REPORT_TYPES = [
        ('financial', 'Financial Report'),
        ('operational', 'Operational Report'),
        ('staff_performance', 'Staff Performance Report'),
        ('customer_analytics', 'Customer Analytics Report'),
        ('location_comparison', 'Location Comparison Report'),
        ('service_analytics', 'Service Analytics Report'),
        ('task_performance', 'Task Performance Report'),
        ('revenue_analytics', 'Revenue Analytics Report'),
    ]
    
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom Range'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='report_templates')
    name = models.CharField(max_length=255)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    description = models.TextField(blank=True, null=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='monthly')
    is_active = models.BooleanField(default=True)
    auto_generate = models.BooleanField(default=False)
    email_recipients = models.JSONField(default=list, blank=True)
    config = models.JSONField(default=dict, blank=True)  # Store report configuration
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Report Template'
        verbose_name_plural = 'Report Templates'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.tenant.name}"

class GeneratedReport(models.Model):
    """Store generated reports"""
    STATUS_CHOICES = [
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]
    
    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='generated_reports')
    template = models.ForeignKey(ReportTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255)
    report_type = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generating')
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='pdf')
    file_path = models.CharField(max_length=500, blank=True, null=True)
    file_url = models.URLField(blank=True, null=True)
    date_from = models.DateTimeField()
    date_to = models.DateTimeField()
    data = models.JSONField(default=dict, blank=True)  # Store report data
    metadata = models.JSONField(default=dict, blank=True)  # Store metadata
    generated_by = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Generated Report'
        verbose_name_plural = 'Generated Reports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.tenant.name} ({self.status})"
    
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

class ReportSchedule(models.Model):
    """Schedule automatic report generation"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='report_schedules')
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    next_run = models.DateTimeField()
    last_run = models.DateTimeField(null=True, blank=True)
    run_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Report Schedule'
        verbose_name_plural = 'Report Schedules'
        ordering = ['next_run']
    
    def __str__(self):
        return f"Schedule: {self.template.name}"

class AnalyticsSnapshot(models.Model):
    """Daily analytics snapshots for faster reporting"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='analytics_snapshots')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='analytics_snapshots', null=True, blank=True)
    snapshot_date = models.DateField()
    
    # Daily metrics
    total_bookings = models.PositiveIntegerField(default=0)
    completed_bookings = models.PositiveIntegerField(default=0)
    cancelled_bookings = models.PositiveIntegerField(default=0)
    no_show_bookings = models.PositiveIntegerField(default=0)
    
    # Revenue metrics
    daily_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    cash_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    mpesa_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    card_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # Task metrics
    total_tasks = models.PositiveIntegerField(default=0)
    completed_tasks = models.PositiveIntegerField(default=0)
    overdue_tasks = models.PositiveIntegerField(default=0)
    
    # Staff metrics
    active_staff = models.PositiveIntegerField(default=0)
    staff_utilization = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    # Customer metrics
    new_customers = models.PositiveIntegerField(default=0)
    repeat_customers = models.PositiveIntegerField(default=0)
    
    # Service metrics
    service_breakdown = models.JSONField(default=dict, blank=True)
    peak_hours = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Analytics Snapshot'
        verbose_name_plural = 'Analytics Snapshots'
        unique_together = ['tenant', 'location', 'snapshot_date']
        ordering = ['-snapshot_date']
    
    def __str__(self):
        location_name = self.location.name if self.location else "All Locations"
        return f"{self.tenant.name} - {location_name} - {self.snapshot_date}"

class CustomReportFilter(models.Model):
    """Custom filters for reports"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='custom_filters')
    name = models.CharField(max_length=255)
    filter_type = models.CharField(max_length=50, choices=[
        ('location', 'Location Filter'),
        ('service', 'Service Filter'),
        ('staff', 'Staff Filter'),
        ('date_range', 'Date Range Filter'),
        ('revenue_range', 'Revenue Range Filter'),
        ('customer_segment', 'Customer Segment Filter'),
    ])
    filter_config = models.JSONField(default=dict)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Custom Report Filter'
        verbose_name_plural = 'Custom Report Filters'
    
    def __str__(self):
        return f"{self.name} - {self.tenant.name}"

class ReportBookmark(models.Model):
    """Save frequently accessed reports"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='report_bookmarks')
    name = models.CharField(max_length=255)
    report_config = models.JSONField()
    is_favorite = models.BooleanField(default=False)
    access_count = models.PositiveIntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Report Bookmark'
        verbose_name_plural = 'Report Bookmarks'
        ordering = ['-last_accessed', '-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.tenant.name}"

class LocationPerformanceMetrics(models.Model):
    """Detailed performance metrics for each location"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='location_metrics')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='performance_metrics')
    date = models.DateField()
    
    # Operational metrics
    bookings_received = models.PositiveIntegerField(default=0)
    bookings_completed = models.PositiveIntegerField(default=0)
    bookings_cancelled = models.PositiveIntegerField(default=0)
    bookings_no_show = models.PositiveIntegerField(default=0)
    
    # Revenue metrics
    gross_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    net_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Efficiency metrics
    average_service_time = models.DurationField(null=True, blank=True)
    staff_utilization_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    customer_satisfaction_score = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    
    # Service breakdown
    service_distribution = models.JSONField(default=dict, blank=True)
    peak_hours_data = models.JSONField(default=dict, blank=True)
    staff_performance = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Location Performance Metric'
        verbose_name_plural = 'Location Performance Metrics'
        unique_together = ['location', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.location.name} - {self.date}"

class TenantAnalyticsSummary(models.Model):
    """Comprehensive analytics summary for tenants"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='analytics_summaries')
    period_start = models.DateField()
    period_end = models.DateField()
    period_type = models.CharField(max_length=20, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ])
    
    # Overall business metrics
    total_locations = models.PositiveIntegerField(default=0)
    active_locations = models.PositiveIntegerField(default=0)
    total_staff = models.PositiveIntegerField(default=0)
    active_staff = models.PositiveIntegerField(default=0)
    
    # Revenue metrics
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    revenue_growth = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    average_revenue_per_location = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Customer metrics
    total_customers = models.PositiveIntegerField(default=0)
    new_customers = models.PositiveIntegerField(default=0)
    repeat_customers = models.PositiveIntegerField(default=0)
    customer_retention_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    # Operational metrics
    total_bookings = models.PositiveIntegerField(default=0)
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    cancellation_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    # Performance insights
    top_performing_location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='top_performance_periods')
    top_performing_staff = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='top_performance_periods')
    most_popular_service = models.CharField(max_length=255, blank=True, null=True)
    
    # Trends and patterns
    trends_data = models.JSONField(default=dict, blank=True)
    insights = models.JSONField(default=list, blank=True)
    recommendations = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Tenant Analytics Summary'
        verbose_name_plural = 'Tenant Analytics Summaries'
        unique_together = ['tenant', 'period_start', 'period_end', 'period_type']
        ordering = ['-period_end']
    
    def __str__(self):
        return f"{self.tenant.name} - {self.period_type} ({self.period_start} to {self.period_end})"
