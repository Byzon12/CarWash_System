from django.urls import path
from .views import (
    AnalyticsDashboardView,
    FinancialReportView,
    OperationalReportView,
)

urlpatterns = [
    # Analytics Dashboard
    path('dashboard/', AnalyticsDashboardView.as_view(), name='analytics-dashboard'),
    #path('quick-stats/', views.quick_stats, name='quick-stats'),
   # path('revenue-trends/', views.revenue_trends, name='revenue-trends'),
    
    # Reports
    path('financial-report/', FinancialReportView.as_view(), name='financial-report'),
    path('operational-report/', OperationalReportView.as_view(), name='operational-report'),
   # path('multi-location-comparison/', views.MultiLocationComparisonView.as_view(), name='multi-location-comparison'),
    
    # Custom Reports
   # path('custom-report/', views.CustomReportBuilderView.as_view(), name='custom-report'),
    #path('export-report/', views.ExportReportView.as_view(), name='export-report'),
   # path('report-status/<uuid:report_id>/', views.ReportStatusView.as_view(), name='report-status'),
    
    # Templates
   # path('templates/', views.ReportTemplateViewSet.as_view(), name='report-templates'),
   
   #report generation
]