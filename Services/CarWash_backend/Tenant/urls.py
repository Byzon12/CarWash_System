
from django.conf import settings
from django.urls import path
from django.conf.urls.static import static
#from .views import TenantProfileListCreateView
from .views import TenantProfileView, TenantLoginView, TenantLogoutView,TenantProfileDetailsView ,CreateEmployeeView, ListEmployeeView, CreateEmployeeSalaryView, DeleteEmployeeView, DeactivateEmployeeView,ActivateEmployeeView, TaskCreateView

urlpatterns = [
  path('login/', TenantLoginView.as_view(), name='tenant-login-view'),
  path('logout/', TenantLogoutView.as_view(), name='tenant-logout-view'),

  path('profile/', TenantProfileView.as_view(), name='tenant-profile-view'),
  path('profile/details/', TenantProfileDetailsView.as_view(), name='tenant-profile-details-view'),

#path for creating employee
#listing employees is not allowed in this case
  path('employees/list/', ListEmployeeView.as_view(), name='list-employee-view'),
  path('employees/update/<int:pk>/', CreateEmployeeSalaryView.as_view(), name='update-employee-salary-view'), #provide location pk in the request data to update employee salary
  path('employees/', CreateEmployeeView.as_view(), name='create-employee-view'),
  
  #deleting an employee 
 path('employees/delete/<int:pk>/', DeleteEmployeeView.as_view(), name='delete-employee-view'),
  path('employees/deactivate/<int:pk>/', DeactivateEmployeeView.as_view(), name='deactivate-employee-view'),
  path('employees/activate/<int:pk>/', ActivateEmployeeView.as_view(), name='activate-employee-view'),
  
  #path for creating tasks and asigning them to employees
  #this will be used by the tenant to create tasks for employees
  path('tasks/create/', TaskCreateView.as_view(), name='create-task-view'),

] 

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
