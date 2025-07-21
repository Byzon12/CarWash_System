from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count, Avg, Q
from datetime import datetime, timedelta, date
from decimal import Decimal
import json

from .models import (
    ReportTemplate, GeneratedReport, ReportSchedule, AnalyticsSnapshot,
    CustomReportFilter, ReportBookmark, LocationPerformanceMetrics,
    TenantAnalyticsSummary
)
from .serializer import (
    ReportTemplateSerializer, GeneratedReportSerializer, FinancialReportSerializer,
    OperationalReportSerializer, AnalyticsDashboardSerializer, CustomReportFilterSerializer,
    ReportBookmarkSerializer
)
from Tenant.models import Tenant, Task
from Location.models import Location
from Staff.models import StaffProfile
from booking.models import booking
from .utils import ReportGenerator, ReportExporter

class AnalyticsDashboardView(generics.GenericAPIView):
    """Enhanced analytics dashboard with comprehensive metrics"""
    permission_classes = [IsAuthenticated]
    serializer_class = AnalyticsDashboardSerializer
    
    def get(self, request, *args, **kwargs):
        """Get comprehensive analytics dashboard data"""
        tenant = request.user
        
        # Get date range from query parameters
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        # Default to last 30 days if no dates provided
        if not date_from or not date_to:
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        
        # Prepare data for serializer
        data = {
            'period_start': start_date,
            'period_end': end_date
        }
        
        serializer = self.get_serializer(data, context={'tenant': tenant, 'request': request})
        
        return Response({
            'success': True,
            'message': 'Analytics dashboard data retrieved successfully',
            'data': serializer.data,
            'meta': {
                'period_start': start_date,
                'period_end': end_date,
                'total_days': (end_date - start_date).days + 1
            }
        })

class FinancialReportView(generics.GenericAPIView):
    """Generate comprehensive financial reports"""
    permission_classes = [IsAuthenticated]
    serializer_class = FinancialReportSerializer
    
    def get(self, request, *args, **kwargs):
        """Generate financial report"""
        tenant = request.user
        
        # Get parameters
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        format_type = request.query_params.get('format', 'json')  # json, pdf, excel, csv
        location_ids = request.query_params.getlist('locations')
        
        # Validate dates
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return Response({
                'success': False,
                'message': 'Invalid date format. Use YYYY-MM-DD'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate report data
        report_data = self._generate_financial_data(tenant, start_date, end_date, location_ids)
        
        if format_type == 'json':
            serializer = self.get_serializer(report_data, context={'tenant': tenant})
            return Response({
                'success': True,
                'message': 'Financial report generated successfully',
                'data': serializer.data
            })
        else:
            # Generate file export
            exporter = ReportExporter()
            file_response = exporter.export_financial_report(
                report_data, format_type, tenant, start_date, end_date
            )
            return file_response
    
    def _generate_financial_data(self, tenant, start_date, end_date, location_ids=None):
        """Generate financial report data"""
        
        # Base query
        bookings_query = booking.objects.filter(
            location__tenant=tenant,
            created_at__date__range=[start_date, end_date]
        )
        
        # Filter by locations if specified
        if location_ids:
            bookings_query = bookings_query.filter(location__id__in=location_ids)
        
        # Calculate revenue metrics
        revenue_data = bookings_query.filter(
            status='completed',
            payment_status='paid'
        ).aggregate(
            total_revenue=Sum('total_amount'),
            cash_revenue=Sum('total_amount', filter=Q(payment_method='cash')),
            mpesa_revenue=Sum('total_amount', filter=Q(payment_method='mpesa')),
            card_revenue=Sum('total_amount', filter=Q(payment_method='visa')),
            avg_order_value=Avg('total_amount')
        )
        
        # Calculate growth metrics
        previous_period_length = (end_date - start_date).days
        previous_start = start_date - timedelta(days=previous_period_length + 1)
        previous_end = start_date - timedelta(days=1)
        
        previous_revenue = booking.objects.filter(
            location__tenant=tenant,
            status='completed',
            payment_status='paid',
            created_at__date__range=[previous_start, previous_end]
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        current_revenue = revenue_data['total_revenue'] or Decimal('0.00')
        
        if previous_revenue > 0:
            revenue_growth = ((current_revenue - previous_revenue) / previous_revenue) * 100
        else:
            revenue_growth = 100 if current_revenue > 0 else 0
        
        return {
            'report_title': f'Financial Report - {start_date} to {end_date}',
            'generated_at': timezone.now(),
            'period_start': start_date,
            'period_end': end_date,
            'total_revenue': revenue_data['total_revenue'] or Decimal('0.00'),
            'cash_revenue': revenue_data['cash_revenue'] or Decimal('0.00'),
            'mpesa_revenue': revenue_data['mpesa_revenue'] or Decimal('0.00'),
            'card_revenue': revenue_data['card_revenue'] or Decimal('0.00'),
            'average_order_value': revenue_data['avg_order_value'] or Decimal('0.00'),
            'revenue_growth': round(revenue_growth, 2)
        }

class OperationalReportView(generics.GenericAPIView):
    """Generate operational performance reports"""
    permission_classes = [IsAuthenticated]
    serializer_class = OperationalReportSerializer
    
    def get(self, request, *args, **kwargs):
        """Generate operational report"""
        tenant = request.user
        
        # Get parameters
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        format_type = request.query_params.get('format', 'json')
        
        # Validate dates
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return Response({
                'success': False,
                'message': 'Invalid date format. Use YYYY-MM-DD'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate report data
        report_data = self._generate_operational_data(tenant, start_date, end_date)
        
        if format_type == 'json':
            serializer = self.get_serializer(report_data, context={'tenant': tenant})
            return Response({
                'success': True,
                'message': 'Operational report generated successfully',
                'data': serializer.data
            })
        else:
            # Generate file export
            exporter = ReportExporter()
            file_response = exporter.export_operational_report(
                report_data, format_type, tenant, start_date, end_date
            )
            return file_response
    
    def _generate_operational_data(self, tenant, start_date, end_date):
        """Generate operational report data"""
        
        # Booking metrics
        bookings_query = booking.objects.filter(
            location__tenant=tenant,
            created_at__date__range=[start_date, end_date]
        )
        
        booking_stats = bookings_query.aggregate(
            total_bookings=Count('id'),
            completed_bookings=Count('id', filter=Q(status='completed')),
            cancelled_bookings=Count('id', filter=Q(status='cancelled')),
            no_show_bookings=Count('id', filter=Q(status='no_show'))
        )
        
        # Task metrics
        task_stats = Task.objects.filter(
            tenant=tenant,
            created_at__date__range=[start_date, end_date]
        ).aggregate(
            total_tasks=Count('task_id'),
            completed_tasks=Count('task_id', filter=Q(status='completed')),
            overdue_tasks=Count('task_id', filter=Q(status='overdue'))
        )
        
        # Calculate rates
        total_bookings = booking_stats['total_bookings']
        completed_bookings = booking_stats['completed_bookings']
        cancelled_bookings = booking_stats['cancelled_bookings']
        
        completion_rate = (completed_bookings / total_bookings * 100) if total_bookings > 0 else 0
        cancellation_rate = (cancelled_bookings / total_bookings * 100) if total_bookings > 0 else 0
        
        total_tasks = task_stats['total_tasks']
        completed_tasks = task_stats['completed_tasks']
        task_efficiency = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            'report_title': f'Operational Report - {start_date} to {end_date}',
            'generated_at': timezone.now(),
            'period_start': start_date,
            'period_end': end_date,
            'total_bookings': total_bookings,
            'completed_bookings': completed_bookings,
            'cancelled_bookings': cancelled_bookings,
            'no_show_bookings': booking_stats['no_show_bookings'],
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'overdue_tasks': task_stats['overdue_tasks'],
            'completion_rate': round(completion_rate, 2),
            'cancellation_rate': round(cancellation_rate, 2),
            'task_efficiency': round(task_efficiency, 2)
        }

class LocationComparisonReportView(generics.GenericAPIView):
    """Compare performance across locations"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """Generate location comparison report"""
        tenant = request.user
        
        # Get parameters
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        metrics = request.query_params.getlist('metrics', ['revenue', 'bookings', 'efficiency'])
        
        # Validate dates
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return Response({
                'success': False,
                'message': 'Invalid date format. Use YYYY-MM-DD'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get all locations for tenant
        locations = Location.objects.filter(tenant=tenant)
        comparison_data = []
        
        for location in locations:
            location_metrics = self._calculate_location_metrics(
                location, start_date, end_date, metrics
            )
            comparison_data.append(location_metrics)
        
        return Response({
            'success': True,
            'message': 'Location comparison report generated successfully',
            'data': {
                'period_start': start_date,
                'period_end': end_date,
                'locations': comparison_data,
                'summary': self._generate_comparison_summary(comparison_data)
            }
        })
    
    def _calculate_location_metrics(self, location, start_date, end_date, metrics):
        """Calculate metrics for a single location"""
        
        # Booking metrics
        bookings = booking.objects.filter(
            location=location,
            created_at__date__range=[start_date, end_date]
        )
        
        total_bookings = bookings.count()
        completed_bookings = bookings.filter(status='completed').count()
        cancelled_bookings = bookings.filter(status='cancelled').count()
        
        # Revenue metrics
        revenue = bookings.filter(
            status='completed',
            payment_status='paid'
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        # Task metrics
        tasks = Task.objects.filter(
            location=location,
            created_at__date__range=[start_date, end_date]
        )
        
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(status='completed').count()
        overdue_tasks = tasks.filter(status='overdue').count()
        
        # Calculate efficiency scores
        booking_efficiency = (completed_bookings / total_bookings * 100) if total_bookings > 0 else 0
        task_efficiency = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        overall_efficiency = (booking_efficiency + task_efficiency) / 2
        
        return {
            'location_id': location.id,
            'location_name': location.name,
            'location_address': location.address,
            'metrics': {
                'bookings': {
                    'total': total_bookings,
                    'completed': completed_bookings,
                    'cancelled': cancelled_bookings,
                    'completion_rate': round(booking_efficiency, 2)
                },
                'revenue': {
                    'total': str(revenue),
                    'average_per_booking': str(revenue / total_bookings if total_bookings > 0 else Decimal('0.00'))
                },
                'tasks': {
                    'total': total_tasks,
                    'completed': completed_tasks,
                    'overdue': overdue_tasks,
                    'efficiency_rate': round(task_efficiency, 2)
                },
                'overall_efficiency': round(overall_efficiency, 2)
            }
        }
    
    def _generate_comparison_summary(self, comparison_data):
        """Generate summary insights from comparison data"""
        if not comparison_data:
            return {}
        
        # Find best and worst performing locations
        best_revenue = max(comparison_data, key=lambda x: float(x['metrics']['revenue']['total']))
        best_efficiency = max(comparison_data, key=lambda x: x['metrics']['overall_efficiency'])
        worst_efficiency = min(comparison_data, key=lambda x: x['metrics']['overall_efficiency'])
        
        # Calculate averages
        total_revenue = sum(float(loc['metrics']['revenue']['total']) for loc in comparison_data)
        total_bookings = sum(loc['metrics']['bookings']['total'] for loc in comparison_data)
        avg_efficiency = sum(loc['metrics']['overall_efficiency'] for loc in comparison_data) / len(comparison_data)
        
        return {
            'best_performing': {
                'revenue': {
                    'location': best_revenue['location_name'],
                    'amount': best_revenue['metrics']['revenue']['total']
                },
                'efficiency': {
                    'location': best_efficiency['location_name'],
                    'score': best_efficiency['metrics']['overall_efficiency']
                }
            },
            'needs_attention': {
                'location': worst_efficiency['location_name'],
                'efficiency_score': worst_efficiency['metrics']['overall_efficiency']
            },
            'overall': {
                'total_revenue': str(total_revenue),
                'total_bookings': total_bookings,
                'average_efficiency': round(avg_efficiency, 2)
            }
        }

class ReportTemplateManagementView(generics.GenericAPIView):
    """Manage report templates"""
    permission_classes = [IsAuthenticated]
    serializer_class = ReportTemplateSerializer
    
    def get(self, request, *args, **kwargs):
        """List all report templates for tenant"""
        tenant = request.user
        templates = ReportTemplate.objects.filter(tenant=tenant).order_by('-created_at')
        serializer = self.get_serializer(templates, many=True)
        
        return Response({
            'success': True,
            'message': 'Report templates retrieved successfully',
            'count': templates.count(),
            'data': serializer.data
        })
    
    def post(self, request, *args, **kwargs):
        """Create new report template"""
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(tenant=request.user)
            return Response({
                'success': True,
                'message': 'Report template created successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Template creation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class GeneratedReportListView(generics.ListAPIView):
    """List generated reports for tenant"""
    permission_classes = [IsAuthenticated]
    serializer_class = GeneratedReportSerializer
    
    def get_queryset(self):
        tenant = self.request.user
        return GeneratedReport.objects.filter(tenant=tenant).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Add filtering
        report_type = request.query_params.get('report_type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)
        
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'message': 'Generated reports retrieved successfully',
            'count': queryset.count(),
            'data': serializer.data
        })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_custom_report(request):
    """Generate a custom report based on user specifications"""
    tenant = request.user
    
    # Get report configuration
    config = request.data
    report_type = config.get('report_type')
    date_from = config.get('date_from')
    date_to = config.get('date_to')
    format_type = config.get('format', 'pdf')
    
    # Validate required fields
    if not all([report_type, date_from, date_to]):
        return Response({
            'success': False,
            'message': 'Missing required fields: report_type, date_from, date_to'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Generate report using report generator utility
        generator = ReportGenerator()
        report = generator.generate_report(tenant, config)
        
        return Response({
            'success': True,
            'message': 'Report generated successfully',
            'data': {
                'report_id': report.id,
                'download_url': report.file_url,
                'status': report.status
            }
        })
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Report generation failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_analytics_data(request):
    """Export analytics data in various formats"""
    tenant = request.user
    
    # Get parameters
    export_type = request.query_params.get('type', 'complete')  # complete, summary, custom
    format_type = request.query_params.get('format', 'excel')   # excel, csv, pdf
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    try:
        exporter = ReportExporter()
        
        if export_type == 'complete':
            file_response = exporter.export_complete_analytics(
                tenant, format_type, date_from, date_to
            )
        elif export_type == 'summary':
            file_response = exporter.export_summary_analytics(
                tenant, format_type, date_from, date_to
            )
        else:
            # Custom export based on request parameters
            file_response = exporter.export_custom_analytics(
                tenant, format_type, request.query_params
            )
        
        return file_response
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Export failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReportBookmarkView(generics.GenericAPIView):
    """Manage report bookmarks"""
    permission_classes = [IsAuthenticated]
    serializer_class = ReportBookmarkSerializer
    
    def get(self, request, *args, **kwargs):
        """List bookmarked reports"""
        tenant = request.user
        bookmarks = ReportBookmark.objects.filter(tenant=tenant).order_by('-last_accessed')
        serializer = self.get_serializer(bookmarks, many=True)
        
        return Response({
            'success': True,
            'message': 'Report bookmarks retrieved successfully',
            'data': serializer.data
        })
    
    def post(self, request, *args, **kwargs):
        """Create new bookmark"""
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(tenant=request.user)
            return Response({
                'success': True,
                'message': 'Report bookmarked successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Bookmark creation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)