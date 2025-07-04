from django.conf import settings
from django.urls import path
from  .views import StaffLoginView, StaffRegistrationView, StaffTaskListView, StaffProfileUpdateView, StaffLogoutView,staffDashboardView

urlpatterns = [
    #staff urls
    
    path('login/', StaffLoginView.as_view(), name='staff_login'),
    path('logout/', StaffLogoutView.as_view(), name='staff_logout'),
    path('register/', StaffRegistrationView.as_view(), name='staff_register'),
    
    #task urls
    path('tasks-list/', StaffTaskListView.as_view(), name='staff_task_list'),
    
    #staffDashboard
    path('dashboard/', staffDashboardView.as_view(), name='staff_dashboard'),
]
