from django.urls import path
from .views import LocationCreateView, LocationUpdateView,LocationDeleteView

urlpatterns = [
    path('create/', LocationCreateView.as_view(), name='location-create'),
    path('update/<int:pk>/', LocationUpdateView.as_view(), name='location-update'),
    path('delete/<int:pk>/', LocationDeleteView.as_view(), name='location-delete'),

   # path('list/', LocationListView.as_view(), name='location-list'),
]
