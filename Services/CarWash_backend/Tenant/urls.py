from django.urls import path
#from .views import TenantProfileListCreateView
from .views import TenantProfileView

urlpatterns = [
  path('profile/', TenantProfileView.as_view(), name='tenant-profile-view'),
]
