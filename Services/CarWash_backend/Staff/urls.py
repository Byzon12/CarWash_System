from django.conf import settings
from django.urls import path
from  .views import StaffLoginView, StaffTaskListView, StaffLogoutView, StaffProfileView, StaffPasswordResetView,  StaffTaskStatisticsView,StaffUpdateTaskStatusView

urlpatterns = [
    #staff urls
    
    path('login/', StaffLoginView.as_view(), name='staff_login'),
    path('logout/', StaffLogoutView.as_view(), name='staff_logout'),
    #staff profile urls
    path('profile/', StaffProfileView.as_view(), name='staff_profile'), #this will be used to retrieve and update the staff profile handle both GET and PUT requests
    
    #staff password reset urls
    path('password-reset/', StaffPasswordResetView.as_view(), name='staff_password_reset'), #this will be used to reset the staff password handle PUT request
    
    #task statistics urls
    path('task-statistics/', StaffTaskStatisticsView.as_view(), name='staff_task_statistics'), #this will be used to retrieve the task statistics for the staff dashboard
    path('tasks/update-status/<int:pk>/', StaffUpdateTaskStatusView.as_view(), name='staff_update_task_status'),

    #task urls
    path('tasks-list/', StaffTaskListView.as_view(), name='staff_task_list'),
    
   
]
