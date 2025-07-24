import io
import json
import logging
from django.db.models import Q, Sum, Count, Avg
from django.http import HttpResponse
from django.template.loader import render_to_string
from decimal import Decimal
from datetime import datetime, timedelta
import csv

# Try to import optional packages with fallbacks
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import xlsxwriter
    XLSXWRITER_AVAILABLE = True
except ImportError:
    XLSXWRITER_AVAILABLE = False

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Enhanced report generator with error handling"""
    
    def __init__(self):
        self.logger = logger
    
    def generate_report(self, tenant, config):
        """Main report generation method"""
        try:
            report_type = config.get('report_type')
            
            if report_type == 'financial':
                return self._generate_financial_report(tenant, config)
            elif report_type == 'operational':
                return self._generate_operational_report(tenant, config)
            elif report_type == 'analytics':
                return self._generate_analytics_report(tenant, config)
            else:
                raise ValueError(f"Unsupported report type: {report_type}")
                
        except Exception as e:
            self.logger.error(f"Report generation failed: {e}")
            raise
    
    def _generate_financial_report(self, tenant, config):
        """Generate financial report data"""
        from .models import GeneratedReport
        from booking.models import booking
        
        start_date = datetime.strptime(config['date_from'], '%Y-%m-%d').date()
        end_date = datetime.strptime(config['date_to'], '%Y-%m-%d').date()
        
        # Generate report data
        bookings = booking.objects.filter(
            location__tenant=tenant,
            created_at__date__range=[start_date, end_date]
        )
        
        revenue_data = bookings.filter(
            status='completed',
            payment_status='paid'
        ).aggregate(
            total_revenue=Sum('total_amount'),
            avg_order_value=Avg('total_amount')
        )
        
        # Create generated report record
        report = GeneratedReport.objects.create(
            tenant=tenant,
            name=f"Financial Report {start_date} to {end_date}",
            report_type='financial',
            date_from=start_date,
            date_to=end_date,
            status='completed',
            data={
                'revenue': revenue_data,
                'period': f"{start_date} to {end_date}",
                'generated_at': datetime.now().isoformat()
            }
        )
        
        return report
    
    def _generate_operational_report(self, tenant, config):
        """Generate operational report data"""
        from .models import GeneratedReport
        from Tenant.models import Task
        
        start_date = datetime.strptime(config['date_from'], '%Y-%m-%d').date()
        end_date = datetime.strptime(config['date_to'], '%Y-%m-%d').date()
        
        # Generate operational metrics
        tasks = Task.objects.filter(
            tenant=tenant,
            created_at__date__range=[start_date, end_date]
        )
        
        task_stats = {
            'total_tasks': tasks.count(),
            'completed_tasks': tasks.filter(status='completed').count(),
            'overdue_tasks': tasks.filter(status='overdue').count()
        }
        
        report = GeneratedReport.objects.create(
            tenant=tenant,
            name=f"Operational Report {start_date} to {end_date}",
            report_type='operational',
            date_from=start_date,
            date_to=end_date,
            status='completed',
            data={
                'tasks': task_stats,
                'period': f"{start_date} to {end_date}",
                'generated_at': datetime.now().isoformat()
            }
        )
        
        return report

class ReportExporter:
    """Enhanced report exporter with fallback options"""
    
    def __init__(self):
        self.logger = logger
    
    def export_financial_report(self, data, format_type, tenant, start_date, end_date):
        """Export financial report in specified format"""
        if format_type == 'pdf' and REPORTLAB_AVAILABLE:
            return self._export_pdf(data, 'financial', tenant.name)
        elif format_type == 'excel' and XLSXWRITER_AVAILABLE:
            return self._export_excel(data, 'financial', tenant.name)
        elif format_type == 'csv':
            return self._export_csv(data, 'financial')
        else:
            return self._export_json(data, 'financial')
    
    def export_operational_report(self, data, format_type, tenant, start_date, end_date):
        """Export operational report in specified format"""
        if format_type == 'pdf' and REPORTLAB_AVAILABLE:
            return self._export_pdf(data, 'operational', tenant.name)
        elif format_type == 'excel' and XLSXWRITER_AVAILABLE:
            return self._export_excel(data, 'operational', tenant.name)
        elif format_type == 'csv':
            return self._export_csv(data, 'operational')
        else:
            return self._export_json(data, 'operational')
    
    def _export_json(self, data, report_type):
        """Fallback JSON export"""
        response = HttpResponse(
            json.dumps(data, indent=2, default=str),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.json"'
        return response
    
    def _export_csv(self, data, report_type):
        """Basic CSV export"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
        
        writer = csv.writer(response)
        
        # Write headers and data based on report type
        if report_type == 'financial':
            writer.writerow(['Metric', 'Value'])
            for key, value in data.items():
                if not isinstance(value, (dict, list)):
                    writer.writerow([key.replace('_', ' ').title(), str(value)])
        
        return response

class AnalyticsProcessor:
    """Process analytics data for insights"""
    
    def __init__(self, tenant):
        self.tenant = tenant
    
    def generate_insights(self, period_data):
        """Generate business insights from analytics data"""
        insights = []
        recommendations = []
        
        # Revenue insights
        if period_data.get('revenue_growth', 0) > 10:
            insights.append("Strong revenue growth detected")
            recommendations.append("Consider expanding successful services")
        elif period_data.get('revenue_growth', 0) < -5:
            insights.append("Revenue decline needs attention")
            recommendations.append("Review pricing and service quality")
        
        # Operational insights
        completion_rate = period_data.get('completion_rate', 0)
        if completion_rate < 80:
            insights.append("Low completion rate affecting performance")
            recommendations.append("Improve operational efficiency and staff training")
        
        return {
            'insights': insights,
            'recommendations': recommendations,
            'performance_score': self._calculate_performance_score(period_data)
        }
    
    def _calculate_performance_score(self, data):
        """Calculate overall performance score"""
        scores = []
        
        # Revenue score (30%)
        revenue_growth = data.get('revenue_growth', 0)
        revenue_score = min(100, max(0, 50 + revenue_growth))
        scores.append(revenue_score * 0.3)
        
        # Completion rate score (40%)
        completion_rate = data.get('completion_rate', 0)
        scores.append(completion_rate * 0.4)
        
        # Customer satisfaction score (30%)
        satisfaction = data.get('customer_satisfaction', 80)  # Default 80%
        scores.append(satisfaction * 0.3)
        
        return round(sum(scores), 1)

class ReportScheduler:
    """Handle scheduled report generation"""
    
    @staticmethod
    def process_scheduled_reports():
        """Process all due scheduled reports"""
        from .models import ReportSchedule
        from django.utils import timezone
        
        due_schedules = ReportSchedule.objects.filter(
            is_active=True,
            next_run__lte=timezone.now()
        )
        
        processed = 0
        for schedule in due_schedules:
            try:
                # Generate report
                generator = ReportGenerator()
                config = {
                    'report_type': schedule.template.report_type,
                    'date_from': (timezone.now().date() - timedelta(days=30)).strftime('%Y-%m-%d'),
                    'date_to': timezone.now().date().strftime('%Y-%m-%d')
                }
                
                report = generator.generate_report(schedule.tenant, config)
                
                # Update schedule
                schedule.last_run = timezone.now()
                schedule.run_count += 1
                schedule.next_run = ReportScheduler._calculate_next_run(
                    schedule.template.frequency
                )
                schedule.save()
                
                processed += 1
                
            except Exception as e:
                logger.error(f"Failed to process schedule {schedule.id}: {e}")
        
        return processed
    
    @staticmethod
    def _calculate_next_run(frequency):
        """Calculate next run time based on frequency"""
        from django.utils import timezone
        
        now = timezone.now()
        
        if frequency == 'daily':
            return now + timedelta(days=1)
        elif frequency == 'weekly':
            return now + timedelta(weeks=1)
        elif frequency == 'monthly':
            return now + timedelta(days=30)
        elif frequency == 'quarterly':
            return now + timedelta(days=90)
        elif frequency == 'yearly':
            return now + timedelta(days=365)
        else:
            return now + timedelta(days=30)  # Default to monthly