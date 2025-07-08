from django.conf import settings
from django.urls import path
from django.conf.urls.static import static
from .views import (
    TenantProfileView, TenantLoginView, TenantLogoutView, TenantProfileDetailsView,
    CreateEmployeeView, ListEmployeeView, CreateEmployeeSalaryView, DeleteEmployeeView,
    DeactivateEmployeeView, ActivateEmployeeView, TaskCreateView, TaskListView,
    TaskDetailView, TaskUpdateStatusView, TenantDashboardStatsView, StaffTaskStatisticsView
)

urlpatterns = [
    # Authentication
    path('login/', TenantLoginView.as_view(), name='tenant-login-view'), # Tenant login view 
    path('logout/', TenantLogoutView.as_view(), name='tenant-logout-view'),

    # Profile management
    path('profile/', TenantProfileView.as_view(), name='tenant-profile-view'),
    path('profile/details/', TenantProfileDetailsView.as_view(), name='tenant-profile-details-view'),

    # Employee management
    path('employees/list/', ListEmployeeView.as_view(), name='list-employee-view'),
    path('employees/', CreateEmployeeView.as_view(), name='create-employee-view'),
    path('employees/update/<int:pk>/', CreateEmployeeSalaryView.as_view(), name='update-employee-salary-view'),# Update employee salary
    path('employees/delete/<int:pk>/', DeleteEmployeeView.as_view(), name='delete-employee-view'),
    path('employees/deactivate/<int:pk>/', DeactivateEmployeeView.as_view(), name='deactivate-employee-view'),
    path('employees/activate/<int:pk>/', ActivateEmployeeView.as_view(), name='activate-employee-view'),
    
    # Task management
    path('tasks/create/', TaskCreateView.as_view(), name='create-task-view'),
    path('tasks/', TaskListView.as_view(), name='list-tasks-view'),
    path('tasks/<int:pk>/', TaskDetailView.as_view(), name='task-detail-view'),
    path('tasks/<int:pk>/status/', TaskUpdateStatusView.as_view(), name='update-task-status-view'),
    
    # Dashboard and statistics
    path('dashboard/stats/', TenantDashboardStatsView.as_view(), name='tenant-dashboard-stats'),
    path('staff/statistics/', StaffTaskStatisticsView.as_view(), name='staff-task-statistics'),
] 

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
