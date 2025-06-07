from django.urls import path
#from .views import TenantProfileListCreateView
from .views import TenantProfileView, TenantLoginView

urlpatterns = [
  path('login/', TenantLoginView.as_view(), name='tenant-login-view'),
  path('profile/', TenantProfileView.as_view(), name='tenant-profile-view'),
]
