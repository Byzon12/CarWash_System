from django.conf import settings
from django.urls import path
from .views import (
    StaffLoginView, StaffTaskListView, StaffLogoutView, StaffProfileView, 
    StaffPasswordResetView, StaffTaskStatisticsView, StaffUpdateTaskStatusView,
    WalkInCustomerCreateView, WalkInCustomerListView, WalkInCustomerUpdateView,
    WalkInTaskCreateView, WalkInTaskListView, WalkInTaskUpdateView, WalkInTaskDetailView,
    WalkInTaskStatusUpdateView, WalkInTaskBulkUpdateView, WalkInTaskTemplateListView,
    WalkInMpesaPaymentInitiateView, WalkInPaymentStatusView, WalkInPaymentListView
)
from .payment_gateways.walkin_mpesa import walkin_mpesa_callback

urlpatterns = [
    # Authentication URLs
    path('login/', StaffLoginView.as_view(), name='staff_login'),
    path('logout/', StaffLogoutView.as_view(), name='staff_logout'),
    path('password-reset/', StaffPasswordResetView.as_view(), name='staff_password_reset'),
    
    # Profile Management URLs
    path('profile/', StaffProfileView.as_view(), name='staff_profile'),
    
    # Dashboard and Statistics URLs
    path('task-statistics/', StaffTaskStatisticsView.as_view(), name='staff_task_statistics'),
    
    # Task Management URLs
    path('tasks/', StaffTaskListView.as_view(), name='staff_task_list'),
    path('tasks/update-status/<int:pk>/', StaffUpdateTaskStatusView.as_view(), name='staff_update_task_status'),
    
    # Walk-in Customer Management URLs
    path('walkin-customers/', WalkInCustomerListView.as_view(), name='walkin_customer_list'),
    path('walkin-customers/create/', WalkInCustomerCreateView.as_view(), name='walkin_customer_create'),
    path('walkin-customers/<int:pk>/update/', WalkInCustomerUpdateView.as_view(), name='walkin_customer_update'),
    
    # Enhanced Walk-in Task Management URLs
    path('walkin-tasks/', WalkInTaskListView.as_view(), name='walkin_task_list'),
    path('walkin-tasks/create/', WalkInTaskCreateView.as_view(), name='walkin_task_create'),
    path('walkin-tasks/<int:pk>/', WalkInTaskDetailView.as_view(), name='walkin_task_detail'),
    path('walkin-tasks/<int:pk>/update/', WalkInTaskUpdateView.as_view(), name='walkin_task_update'),
    path('walkin-tasks/<int:pk>/status/', WalkInTaskStatusUpdateView.as_view(), name='walkin_task_status_update'),
    path('walkin-tasks/bulk-update/', WalkInTaskBulkUpdateView.as_view(), name='walkin_task_bulk_update'),
    path('walkin-tasks/templates/', WalkInTaskTemplateListView.as_view(), name='walkin_task_templates'),
    
    # Walk-in Payment URLs
    path('walkin-payments/', WalkInPaymentListView.as_view(), name='walkin_payment_list'),
    path('walkin-payments/initiate-mpesa/', WalkInMpesaPaymentInitiateView.as_view(), name='walkin_mpesa_initiate'),
    path('walkin-payments/<int:payment_id>/status/', WalkInPaymentStatusView.as_view(), name='walkin_payment_status'),
    
    # M-Pesa Callback URL
    path('walkin-customers/mpesa-callback/', walkin_mpesa_callback, name='walkin_mpesa_callback'),
]
