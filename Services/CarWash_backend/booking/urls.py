from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # Customer booking management
    path('create/', views.BookingCreateView.as_view(), name='booking-create'),
    path('list/', views.BookingListView.as_view(), name='booking-list'),
    path('history/', views.BookingHistoryView.as_view(), name='booking-history'),
    path('<int:pk>/', views.BookingDetailView.as_view(), name='booking-detail'),
    path('<int:pk>/update/', views.BookingUpdateView.as_view(), name='booking-update'),
    path('<int:pk>/cancel/', views.BookingCancelView.as_view(), name='booking-cancel'),
    path('delete/<int:pk>/', views.BookingDeleteView.as_view(), name='booking-delete'),

    # Payment management
    path('payment/initiate/', views.PaymentInitiationView.as_view(), name='payment-initiate'),
    path('payment/status/', views.check_payment_status, name='payment-status'),
    path('<int:pk>/payment/initiate/', views.PaymentInitiationView.as_view(), name='payment-initiate-url'),
    
    # Payment callbacks
    path('mpesa-callback/', views.mpesa_callback, name='mpesa-callback'),
    
    # Tenant booking management (for admin/staff)
    path('tenant/list/', views.TenantBookingListView.as_view(), name='tenant-booking-list'),
    path('tenant/stats/', views.TenantBookingStatsView.as_view(), name='tenant-booking-stats'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)