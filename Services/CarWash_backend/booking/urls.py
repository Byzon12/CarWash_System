from django.urls import path
from .views import BookingCreateView, BookingUpdateView, BookingListView, BookingListView
urlpatterns = [
    path('create/', BookingCreateView.as_view(), name='booking_create'),
    path('update/<int:pk>/', BookingUpdateView.as_view(), name='booking_update'),
    path('list/', BookingListView.as_view(), name='booking_list'),
]