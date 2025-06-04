from django.urls import path
from .views import RegisterUserView, ListUserView, LoginUserView, CustomerProfileView, PasswordResetView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


urlpatterns = [
    
    # JWT authentication endpoints
    # These endpoints are used to obtain and refresh JWT tokens
   # path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    #path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # User management endpoints
    # These endpoints are used for user registration and listing users
    path('register/', RegisterUserView.as_view(), name='register_user'),
    path('login/', LoginUserView.as_view(), name='login_user'),
    path('list/', ListUserView.as_view(), name='list_users'),
    
    #password reset endpoint
    # This endpoint is used to reset the password for a user
    path('password-reset/', PasswordResetView.as_view(), name='password_reset'),
    
    path('profile/', CustomerProfileView.as_view(), name='customer_profile'),
]
