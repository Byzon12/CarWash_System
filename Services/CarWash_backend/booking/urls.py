from django.urls import path
from .views import BookingCreateView, BookingUpdateView, BookingListView, BookingListView, BookingCancellationView
urlpatterns = [
    path('create/', BookingCreateView.as_view(), name='booking_create'),
    path('update/<int:pk>/', BookingUpdateView.as_view(), name='booking_update'),
    path('list/', BookingListView.as_view(), name='booking_list'),
    path('cancel/<int:pk>/', BookingCancellationView.as_view(), name='booking_cancel'),
    
]