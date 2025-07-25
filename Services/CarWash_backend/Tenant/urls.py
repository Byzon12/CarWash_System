from django.conf import settings
from django.urls import path
from django.conf.urls.static import static
from .views import (
    TenantProfileView, TenantLoginView, TenantLogoutView, TenantProfileDetailsView,
    CreateEmployeeView, ListEmployeeView, CreateEmployeeSalaryView, DeleteEmployeeView,
    DeactivateEmployeeView, ActivateEmployeeView, TaskCreateView, TaskListView,
    TaskDetailView, TaskUpdateStatusView, TenantDashboardStatsView, StaffTaskStatisticsView,
    ListEmployeeRolesView, TaskSummaryView, CarCheckOutItemsView, CarCheckInItemsView
)

urlpatterns = [
    # Authentication
    path('login/', TenantLoginView.as_view(), name='tenant-login-view'), # Tenant login view 
    path('logout/', TenantLogoutView.as_view(), name='tenant-logout-view'),

    # Profile management
    path('profile/', TenantProfileView.as_view(), name='tenant-profile-view'),
    path('profile/details/', TenantProfileDetailsView.as_view(), name='tenant-profile-details-view'),

    # Employee management
    path('employees/list/', ListEmployeeView.as_view(), name='list-employee-view'),#list all employees for the tenant
    path('employees/create/', CreateEmployeeView.as_view(), name='create-employee-view'),# Create a new employee
    path('employees/update/<int:pk>/', CreateEmployeeSalaryView.as_view(), name='update-employee-salary-view'),# uUpdate employee role and salary
    path('employees/delete/<int:pk>/', DeleteEmployeeView.as_view(), name='delete-employee-view'),
    path('employees/deactivate/<int:pk>/', DeactivateEmployeeView.as_view(), name='deactivate-employee-view'),
    path('employees/activate/<int:pk>/', ActivateEmployeeView.as_view(), name='activate-employee-view'),

    # Employee role management
    path('roles/create/', CreateEmployeeSalaryView.as_view(), name='create-employee-role'),
    path('roles/', ListEmployeeRolesView.as_view(), name='list-employee-roles'),

    # Task management
    path('tasks/create/', TaskCreateView.as_view(), name='create-task-view'),
    path('tasks/', TaskListView.as_view(), name='list-tasks-view'),
    path('tasks/<int:pk>/', TaskDetailView.as_view(), name='task-detail-view'),
    path('tasks/<int:pk>/status/', TaskUpdateStatusView.as_view(), name='update-task-status-view'),# Update task status patch method

    # Enhanced task management with check-in items
    path('tasks/create/', TaskCreateView.as_view(), name='create-task-view'),
    path('tasks/', TaskListView.as_view(), name='list-tasks-view'),
    path('tasks/<int:pk>/', TaskDetailView.as_view(), name='task-detail-view'),
    path('tasks/<int:pk>/status/', TaskUpdateStatusView.as_view(), name='update-task-status-view'),
    
    # Car check-in/out management
    path('tasks/<int:task_id>/checkins/', CarCheckInItemsView.as_view(), name='task-checkin-items'),
    path('tasks/<int:task_id>/summary/', TaskSummaryView.as_view(), name='task-checkin-summary'),
    path('checkins/<int:pk>/checkout/', CarCheckOutItemsView.as_view(), name='car-checkout'),

    # Dashboard and statistics
    path('dashboard/stats/', TenantDashboardStatsView.as_view(), name='tenant-dashboard-stats'),
    path('staff/statistics/', StaffTaskStatisticsView.as_view(), name='staff-task-statistics'),
] 

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
