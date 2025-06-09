from django.urls import path
#from .views import TenantProfileListCreateView
from .views import TenantProfileView, TenantLoginView, TenantLogoutView, CreateEmployeeView, ListEmployeeView, UpdateEmployeeSalaryView

urlpatterns = [
  path('login/', TenantLoginView.as_view(), name='tenant-login-view'),
  path('logout/', TenantLogoutView.as_view(), name='tenant-logout-view'),

  path('profile/', TenantProfileView.as_view(), name='tenant-profile-view'),
  
#path for creating employee
#listing employees is not allowed in this case
  path('employees/list/', ListEmployeeView.as_view(), name='list-employee-view'),
  path('employees/update/<int:pk>/', UpdateEmployeeSalaryView.as_view(), name='update-employee-salary-view'),
  path('employees/', CreateEmployeeView.as_view(), name='create-employee-view'),
]
