from django.conf import settings
from django.urls import path
from  .views import StaffLoginView, StaffRegistrationView

urlpatterns = [
    #staff urls
    
    path('login/', StaffLoginView.as_view(), name='staff_login'),
    path('register/', StaffRegistrationView.as_view(), name='staff_register'),
]
