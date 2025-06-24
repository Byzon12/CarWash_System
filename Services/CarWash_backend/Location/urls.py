from django.urls import path
from .views import LocationCreateView, LocationUpdateView,LocationDeleteView, ServiceCreateView, ServiceUpdateView, ServiceDeleteView, ServiceDeleteView, LocationServiceCreateView, LocationServiceDeleteView, LocationServiceListView,LocationServiceDetailView, LocationListView,ServiceListView

urlpatterns = [
    path('create/', LocationCreateView.as_view(), name='location-create'),
    path('update/<int:pk>/', LocationUpdateView.as_view(), name='location-update'),
    path('delete/<int:pk>/', LocationDeleteView.as_view(), name='location-delete'),
    path('list/', LocationListView.as_view(), name='location-list'),

   # path('list/', LocationListView.as_view(), name='location-list'),
   
   #services routing 
   path('services/create/', ServiceCreateView.as_view(), name='service-create'),
    path('services/list/', ServiceListView.as_view(), name='service-list'),
   path('services/update/<int:pk>/', ServiceUpdateView.as_view(), name='service-update'),
   path('services/delete/<int:pk>/', ServiceDeleteView.as_view(), name='service-delete'),
   
   #location service routing
    path('location-services/create/', LocationServiceCreateView.as_view(), name='location-service-create'),
    path('location-services/delete/<int:pk>/', LocationServiceDeleteView.as_view(), name='location-service-delete'),
    path('location-services/list/', LocationServiceListView.as_view(), name='location-service-list'),
    path('location-services/detail/<int:pk>/', LocationServiceDetailView.as_view(), name='location-service-detail'),
   
    
]
