from django.urls import path
#from .views import TenantProfileListCreateView
from .views import TenantProfileView, TenantLoginView, TenantLogoutView,TenantProfileDetailsView ,CreateEmployeeView, ListEmployeeView, CreateEmployeeSalaryView, DeleteEmployeeView, DeactivateEmployeeView

urlpatterns = [
  path('login/', TenantLoginView.as_view(), name='tenant-login-view'),
  path('logout/', TenantLogoutView.as_view(), name='tenant-logout-view'),

  path('profile/', TenantProfileView.as_view(), name='tenant-profile-view'),
  path('profile/details/', TenantProfileDetailsView.as_view(), name='tenant-profile-details-view'),

#path for creating employee
#listing employees is not allowed in this case
  path('employees/list/', ListEmployeeView.as_view(), name='list-employee-view'),
  path('employees/update/', CreateEmployeeSalaryView.as_view(), name='update-employee-salary-view'),
  path('employees/', CreateEmployeeView.as_view(), name='create-employee-view'),
  
  #deleting an employee 
 path('employees/delete/<int:pk>/', DeleteEmployeeView.as_view(), name='delete-employee-view'),
  path('employees/deactivate/<int:pk>/', DeactivateEmployeeView.as_view(), name='deactivate-employee-view'),
  # In your urls.py
#path('employee/<int:pk>/delete/', DeleteEmployeeView.as_view(), name='delete_employee')

]
