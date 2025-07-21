from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Count, Avg, Q
from decimal import Decimal
from datetime import datetime, timedelta, date
from .models import (
    ReportTemplate, GeneratedReport, ReportSchedule, AnalyticsSnapshot,
    CustomReportFilter, ReportBookmark, LocationPerformanceMetrics,
    TenantAnalyticsSummary
)
from Tenant.models import Tenant, Task
from Location.models import Location
from Staff.models import StaffProfile
from booking.models import booking

# Importing models to avoid circular imports
def get_booking_model():
    from booking.models import booking
    return booking

def get_task_model():
    from Tenant.models import Task
    return Task

class ReportTemplateSerializer(serializers.ModelSerializer):
    """Serializer for report templates"""
    
    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'report_type', 'description', 'frequency',
            'is_active', 'auto_generate', 'email_recipients', 'config',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_config(self, value):
        """Validate report configuration"""
        required_keys = ['date_range', 'locations', 'metrics']
        for key in required_keys:
            if key not in value:
                raise serializers.ValidationError(f"Missing required config key: {key}")
        return value

class GeneratedReportSerializer(serializers.ModelSerializer):
    """Serializer for generated reports"""
    download_url = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    generated_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = GeneratedReport
        fields = [
            'id', 'name', 'report_type', 'status', 'format', 'download_url',
            'date_from', 'date_to', 'template_name', 'generated_by_name',
            'is_expired', 'created_at', 'expires_at'
        ]
        read_only_fields = ['id', 'status', 'created_at']
    
    def get_download_url(self, obj):
        """Get download URL for the report"""
        if obj.file_url:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file_url)
            return obj.file_url
        return None
    
    def get_generated_by_name(self, obj):
        """Get name of user who generated the report"""
        if obj.generated_by:
            return f"{obj.generated_by.first_name} {obj.generated_by.last_name}".strip() or obj.generated_by.username
        return "System"

class FinancialReportSerializer(serializers.Serializer):
    """Comprehensive financial report serializer"""
    
    # Report metadata
    report_title = serializers.CharField(read_only=True)
    generated_at = serializers.DateTimeField(read_only=True)
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    
    # Revenue breakdown
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    cash_revenue = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    mpesa_revenue = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    card_revenue = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    # Location breakdown
    location_revenue = serializers.SerializerMethodField()
    
    # Service breakdown
    service_revenue = serializers.SerializerMethodField()
    
    # Trends
    daily_revenue_trend = serializers.SerializerMethodField()
    monthly_comparison = serializers.SerializerMethodField()
    
    # Key metrics
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    revenue_growth = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    def get_location_revenue(self, obj):
        """Get revenue breakdown by location"""
        tenant = self.context.get('tenant')
        if not tenant:
            return []
        
        Booking = get_booking_model()
        locations = Location.objects.filter(tenant=tenant)
        
        location_data = []
        for location in locations:
            revenue = Booking.objects.filter(
                location=location,
                status='completed',
                payment_status='paid',
                created_at__date__range=[obj['period_start'], obj['period_end']]
            ).aggregate(
                total=Sum('total_amount')
            )['total'] or Decimal('0.00')
            
            bookings_count = Booking.objects.filter(
                location=location,
                status='completed',
                created_at__date__range=[obj['period_start'], obj['period_end']]
            ).count()
            
            location_data.append({
                'location_id': location.id,
                'location_name': location.name,
                'revenue': str(revenue),
                'bookings_count': bookings_count,
                'average_per_booking': str(revenue / bookings_count if bookings_count > 0 else Decimal('0.00'))
            })
        
        return location_data
    
    def get_service_revenue(self, obj):
        """Get revenue breakdown by service"""
        tenant = self.context.get('tenant')
        if not tenant:
            return []
        
        Booking = get_booking_model()
        
        # Get service revenue data
        bookings = Booking.objects.filter(
            location__tenant=tenant,
            status='completed',
            payment_status='paid',
            created_at__date__range=[obj['period_start'], obj['period_end']]
        ).select_related('location_service')
        
        service_data = {}
        for booking in bookings:
            if booking.location_service:
                service_name = booking.location_service.name
                if service_name not in service_data:
                    service_data[service_name] = {
                        'revenue': Decimal('0.00'),
                        'count': 0
                    }
                service_data[service_name]['revenue'] += booking.total_amount
                service_data[service_name]['count'] += 1
        
        return [
            {
                'service_name': name,
                'revenue': str(data['revenue']),
                'bookings_count': data['count'],
                'percentage': round((data['revenue'] / obj.get('total_revenue', Decimal('1.00'))) * 100, 2)
            }
            for name, data in service_data.items()
        ]
    
    def get_daily_revenue_trend(self, obj):
        """Get daily revenue trend for the period"""
        tenant = self.context.get('tenant')
        if not tenant:
            return []
        
        Booking = get_booking_model()
        
        # Generate daily revenue data
        current_date = obj['period_start']
        end_date = obj['period_end']
        daily_data = []
        
        while current_date <= end_date:
            daily_revenue = Booking.objects.filter(
                location__tenant=tenant,
                status='completed',
                payment_status='paid',
                created_at__date=current_date
            ).aggregate(
                total=Sum('total_amount')
            )['total'] or Decimal('0.00')
            
            daily_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'revenue': str(daily_revenue)
            })
            
            current_date += timedelta(days=1)
        
        return daily_data
    
    def get_monthly_comparison(self, obj):
        """Compare with previous month"""
        tenant = self.context.get('tenant')
        if not tenant:
            return {}
        
        Booking = get_booking_model()
        
        # Calculate previous period
        period_length = (obj['period_end'] - obj['period_start']).days
        previous_start = obj['period_start'] - timedelta(days=period_length + 1)
        previous_end = obj['period_start'] - timedelta(days=1)
        
        previous_revenue = Booking.objects.filter(
            location__tenant=tenant,
            status='completed',
            payment_status='paid',
            created_at__date__range=[previous_start, previous_end]
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        
        current_revenue = obj.get('total_revenue', Decimal('0.00'))
        
        if previous_revenue > 0:
            growth = ((current_revenue - previous_revenue) / previous_revenue) * 100
        else:
            growth = 100 if current_revenue > 0 else 0
        
        return {
            'previous_revenue': str(previous_revenue),
            'current_revenue': str(current_revenue),
            'growth_percentage': round(growth, 2),
            'growth_amount': str(current_revenue - previous_revenue)
        }

class OperationalReportSerializer(serializers.Serializer):
    """Operational performance report serializer"""
    
    # Report metadata
    report_title = serializers.CharField(read_only=True)
    generated_at = serializers.DateTimeField(read_only=True)
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    
    # Booking metrics
    total_bookings = serializers.IntegerField(read_only=True)
    completed_bookings = serializers.IntegerField(read_only=True)
    cancelled_bookings = serializers.IntegerField(read_only=True)
    no_show_bookings = serializers.IntegerField(read_only=True)
    
    # Task metrics
    total_tasks = serializers.IntegerField(read_only=True)
    completed_tasks = serializers.IntegerField(read_only=True)
    overdue_tasks = serializers.IntegerField(read_only=True)
    
    # Staff performance
    staff_performance = serializers.SerializerMethodField()
    
    # Location performance
    location_performance = serializers.SerializerMethodField()
    
    # Efficiency metrics
    completion_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    cancellation_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    task_efficiency = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    def get_staff_performance(self, obj):
        """Get staff performance metrics"""
        tenant = self.context.get('tenant')
        if not tenant:
            return []
        
        Task = get_task_model()
        staff_profiles = StaffProfile.objects.filter(tenant=tenant)
        
        staff_data = []
        for staff in staff_profiles:
            tasks_assigned = Task.objects.filter(
                assigned_to=staff,
                created_at__date__range=[obj['period_start'], obj['period_end']]
            )
            
            total_tasks = tasks_assigned.count()
            completed_tasks = tasks_assigned.filter(status='completed').count()
            overdue_tasks = tasks_assigned.filter(status='overdue').count()
            
            staff_data.append({
                'staff_id': staff.id,
                'staff_name': f"{staff.first_name} {staff.last_name}".strip() or staff.username,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'overdue_tasks': overdue_tasks,
                'completion_rate': round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 2),
                'efficiency_score': self._calculate_efficiency_score(completed_tasks, overdue_tasks, total_tasks)
            })
        
        return sorted(staff_data, key=lambda x: x['efficiency_score'], reverse=True)
    
    def get_location_performance(self, obj):
        """Get location performance metrics"""
        tenant = self.context.get('tenant')
        if not tenant:
            return []
        
        Booking = get_booking_model()
        locations = Location.objects.filter(tenant=tenant)
        
        location_data = []
        for location in locations:
            bookings = Booking.objects.filter(
                location=location,
                created_at__date__range=[obj['period_start'], obj['period_end']]
            )
            
            total_bookings = bookings.count()
            completed_bookings = bookings.filter(status='completed').count()
            cancelled_bookings = bookings.filter(status='cancelled').count()
            
            location_data.append({
                'location_id': location.id,
                'location_name': location.name,
                'total_bookings': total_bookings,
                'completed_bookings': completed_bookings,
                'cancelled_bookings': cancelled_bookings,
                'completion_rate': round((completed_bookings / total_bookings * 100) if total_bookings > 0 else 0, 2),
                'cancellation_rate': round((cancelled_bookings / total_bookings * 100) if total_bookings > 0 else 0, 2)
            })
        
        return sorted(location_data, key=lambda x: x['completion_rate'], reverse=True)
    
    def _calculate_efficiency_score(self, completed, overdue, total):
        """Calculate efficiency score for staff"""
        if total == 0:
            return 0
        
        completion_score = (completed / total) * 70  # 70% weight for completion
        overdue_penalty = (overdue / total) * 30     # 30% penalty for overdue
        
        return max(0, round(completion_score - overdue_penalty, 2))

class AnalyticsDashboardSerializer(serializers.Serializer):
    """Enhanced analytics dashboard serializer"""
    
    # Overview metrics
    overview = serializers.SerializerMethodField()
    
    # Charts data
    revenue_chart = serializers.SerializerMethodField()
    bookings_chart = serializers.SerializerMethodField()
    location_comparison = serializers.SerializerMethodField()
    service_popularity = serializers.SerializerMethodField()
    
    # KPIs
    key_performance_indicators = serializers.SerializerMethodField()
    
    # Trends
    trends_analysis = serializers.SerializerMethodField()
    
    # Quick stats
    quick_stats = serializers.SerializerMethodField()
    
    def get_overview(self, obj):
        """Get overview statistics"""
        tenant = self.context.get('tenant')
        period_start = obj.get('period_start')
        period_end = obj.get('period_end')
        
        if not tenant:
            return {}
        
        Booking = get_booking_model()
        Task = get_task_model()
        
        # Booking metrics
        total_bookings = Booking.objects.filter(
            location__tenant=tenant,
            created_at__date__range=[period_start, period_end]
        ).count()
        
        completed_bookings = Booking.objects.filter(
            location__tenant=tenant,
            status='completed',
            created_at__date__range=[period_start, period_end]
        ).count()
        
        # Revenue metrics
        total_revenue = Booking.objects.filter(
            location__tenant=tenant,
            status='completed',
            payment_status='paid',
            created_at__date__range=[period_start, period_end]
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        # Task metrics
        total_tasks = Task.objects.filter(
            tenant=tenant,
            created_at__date__range=[period_start, period_end]
        ).count()
        
        completed_tasks = Task.objects.filter(
            tenant=tenant,
            status='completed',
            created_at__date__range=[period_start, period_end]
        ).count()
        
        return {
            'bookings': {
                'total': total_bookings,
                'completed': completed_bookings,
                'completion_rate': round((completed_bookings / total_bookings * 100) if total_bookings > 0 else 0, 2)
            },
            'revenue': {
                'total': str(total_revenue),
                'average_per_booking': str(total_revenue / total_bookings if total_bookings > 0 else Decimal('0.00'))
            },
            'tasks': {
                'total': total_tasks,
                'completed': completed_tasks,
                'completion_rate': round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 2)
            },
            'locations': {
                'total': Location.objects.filter(tenant=tenant).count(),
                'active': Location.objects.filter(tenant=tenant).count()  # Assuming all are active
            },
            'staff': {
                'total': StaffProfile.objects.filter(tenant=tenant).count(),
                'active': StaffProfile.objects.filter(tenant=tenant, is_active=True).count()
            }
        }
    
    def get_revenue_chart(self, obj):
        """Get revenue chart data"""
        tenant = self.context.get('tenant')
        period_start = obj.get('period_start')
        period_end = obj.get('period_end')
        
        if not tenant:
            return []
        
        Booking = get_booking_model()
        
        # Generate daily revenue data
        chart_data = []
        current_date = period_start
        
        while current_date <= period_end:
            daily_revenue = Booking.objects.filter(
                location__tenant=tenant,
                status='completed',
                payment_status='paid',
                created_at__date=current_date
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            
            chart_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'revenue': float(daily_revenue)
            })
            
            current_date += timedelta(days=1)
        
        return chart_data
    
    def get_bookings_chart(self, obj):
        """Get bookings trend chart data"""
        tenant = self.context.get('tenant')
        period_start = obj.get('period_start')
        period_end = obj.get('period_end')
        
        if not tenant:
            return []
        
        Booking = get_booking_model()
        
        chart_data = []
        current_date = period_start
        
        while current_date <= period_end:
            daily_bookings = Booking.objects.filter(
                location__tenant=tenant,
                created_at__date=current_date
            ).count()
            
            completed_bookings = Booking.objects.filter(
                location__tenant=tenant,
                status='completed',
                created_at__date=current_date
            ).count()
            
            chart_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'total_bookings': daily_bookings,
                'completed_bookings': completed_bookings
            })
            
            current_date += timedelta(days=1)
        
        return chart_data
    
    def get_location_comparison(self, obj):
        """Get location performance comparison"""
        tenant = self.context.get('tenant')
        period_start = obj.get('period_start')
        period_end = obj.get('period_end')
        
        if not tenant:
            return []
        
        Booking = get_booking_model()
        locations = Location.objects.filter(tenant=tenant)
        
        comparison_data = []
        for location in locations:
            revenue = Booking.objects.filter(
                location=location,
                status='completed',
                payment_status='paid',
                created_at__date__range=[period_start, period_end]
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            
            bookings = Booking.objects.filter(
                location=location,
                created_at__date__range=[period_start, period_end]
            ).count()
            
            comparison_data.append({
                'location_name': location.name,
                'revenue': float(revenue),
                'bookings': bookings,
                'average_revenue': float(revenue / bookings if bookings > 0 else Decimal('0.00'))
            })
        
        return sorted(comparison_data, key=lambda x: x['revenue'], reverse=True)
    
    def get_service_popularity(self, obj):
        """Get service popularity data"""
        tenant = self.context.get('tenant')
        period_start = obj.get('period_start')
        period_end = obj.get('period_end')
        
        if not tenant:
            return []
        
        Booking = get_booking_model()
        
        # Get service popularity
        bookings = Booking.objects.filter(
            location__tenant=tenant,
            created_at__date__range=[period_start, period_end]
        ).select_related('location_service')
        
        service_data = {}
        total_bookings = bookings.count()
        
        for booking in bookings:
            if booking.location_service:
                service_name = booking.location_service.name
                if service_name not in service_data:
                    service_data[service_name] = {
                        'count': 0,
                        'revenue': Decimal('0.00')
                    }
                service_data[service_name]['count'] += 1
                if booking.status == 'completed' and booking.payment_status == 'paid':
                    service_data[service_name]['revenue'] += booking.total_amount
        
        popularity_data = []
        for service_name, data in service_data.items():
            popularity_data.append({
                'service_name': service_name,
                'bookings_count': data['count'],
                'revenue': float(data['revenue']),
                'popularity_percentage': round((data['count'] / total_bookings * 100) if total_bookings > 0 else 0, 2)
            })
        
        return sorted(popularity_data, key=lambda x: x['bookings_count'], reverse=True)
    
    def get_key_performance_indicators(self, obj):
        """Get key performance indicators"""
        tenant = self.context.get('tenant')
        period_start = obj.get('period_start')
        period_end = obj.get('period_end')
        
        # Calculate previous period for comparison
        period_length = (period_end - period_start).days
        prev_start = period_start - timedelta(days=period_length + 1)
        prev_end = period_start - timedelta(days=1)
        
        # Current period metrics
        current_metrics = self._calculate_period_metrics(tenant, period_start, period_end)
        previous_metrics = self._calculate_period_metrics(tenant, prev_start, prev_end)
        
        def calculate_change(current, previous):
            if previous == 0:
                return 100 if current > 0 else 0
            return round(((current - previous) / previous) * 100, 2)
        
        return {
            'revenue': {
                'current': current_metrics['revenue'],
                'previous': previous_metrics['revenue'],
                'change': calculate_change(current_metrics['revenue'], previous_metrics['revenue'])
            },
            'bookings': {
                'current': current_metrics['bookings'],
                'previous': previous_metrics['bookings'],
                'change': calculate_change(current_metrics['bookings'], previous_metrics['bookings'])
            },
            'completion_rate': {
                'current': current_metrics['completion_rate'],
                'previous': previous_metrics['completion_rate'],
                'change': round(current_metrics['completion_rate'] - previous_metrics['completion_rate'], 2)
            },
            'average_order_value': {
                'current': current_metrics['aov'],
                'previous': previous_metrics['aov'],
                'change': calculate_change(current_metrics['aov'], previous_metrics['aov'])
            }
        }
    
    def get_trends_analysis(self, obj):
        """Get trends analysis"""
        return {
            'revenue_trend': 'increasing',  # This would be calculated based on actual data
            'booking_trend': 'stable',
            'customer_satisfaction': 'improving',
            'operational_efficiency': 'increasing'
        }
    
    def get_quick_stats(self, obj):
        """Get quick statistics for dashboard widgets"""
        tenant = self.context.get('tenant')
        
        if not tenant:
            return {}
        
        # Today's stats
        today = date.today()
        
        Booking = get_booking_model()
        Task = get_task_model()
        
        return {
            'today': {
                'bookings': Booking.objects.filter(
                    location__tenant=tenant,
                    created_at__date=today
                ).count(),
                'revenue': str(Booking.objects.filter(
                    location__tenant=tenant,
                    status='completed',
                    payment_status='paid',
                    created_at__date=today
                ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')),
                'tasks_completed': Task.objects.filter(
                    tenant=tenant,
                    status='completed',
                    updated_at__date=today
                ).count()
            },
            'pending': {
                'tasks': Task.objects.filter(
                    tenant=tenant,
                    status='pending'
                ).count(),
                'bookings': Booking.objects.filter(
                    location__tenant=tenant,
                    status='pending'
                ).count()
            }
        }
    
    def _calculate_period_metrics(self, tenant, start_date, end_date):
        """Calculate metrics for a given period"""
        if not tenant:
            return {'revenue': 0, 'bookings': 0, 'completion_rate': 0, 'aov': 0}
        
        Booking = get_booking_model()
        
        period_bookings = Booking.objects.filter(
            location__tenant=tenant,
            created_at__date__range=[start_date, end_date]
        )
        
        total_bookings = period_bookings.count()
        completed_bookings = period_bookings.filter(status='completed').count()
        
        revenue = period_bookings.filter(
            status='completed',
            payment_status='paid'
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        completion_rate = (completed_bookings / total_bookings * 100) if total_bookings > 0 else 0
        aov = revenue / completed_bookings if completed_bookings > 0 else Decimal('0.00')
        
        return {
            'revenue': float(revenue),
            'bookings': total_bookings,
            'completion_rate': round(completion_rate, 2),
            'aov': float(aov)
        }

class CustomReportFilterSerializer(serializers.ModelSerializer):
    """Serializer for custom report filters"""
    
    class Meta:
        model = CustomReportFilter
        fields = ['id', 'name', 'filter_type', 'filter_config', 'is_default', 'created_at']
        read_only_fields = ['id', 'created_at']

class ReportBookmarkSerializer(serializers.ModelSerializer):
    """Serializer for report bookmarks"""
    
    class Meta:
        model = ReportBookmark
        fields = [
            'id', 'name', 'report_config', 'is_favorite', 'access_count',
            'last_accessed', 'created_at'
        ]
        read_only_fields = ['id', 'access_count', 'last_accessed', 'created_at']