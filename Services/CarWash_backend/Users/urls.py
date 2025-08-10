from django.urls import path
from .views import (
    RegisterUserView, ListUserView, LoginUserView, CustomerProfileView, 
    PasswordResetView, PasswordResetConfirmView, PasswordChangeView, LogoutUserView,
    # Flutter-optimized views
    FlutterRegisterView, FlutterLoginView, FlutterProfileView, FlutterLogoutView,
    flutter_user_status, flutter_check_username, flutter_check_email,
    # Enhanced location views
    UserAvailableLocationsView,location_services_list,
    # Loyalty Points views
    LoyaltyPointsDashboardView, LoyaltyPointsHistoryView, 
    redeem_loyalty_points, loyalty_tier_info
   # search_locations, location_details, 
   #add favorites views
    , AddFavoriteView, RemoveFavoriteView, ListFavoritesView
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


urlpatterns = [
    # Original endpoints (keep for backward compatibility)
    path('register/', RegisterUserView.as_view(), name='register_user'),# post method
    path('login/', LoginUserView.as_view(), name='login_user'),#
    #path('list/', ListUserView.as_view(), name='list_users'),
    path('password-reset/', PasswordResetView.as_view(), name='password_reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset-change/', PasswordChangeView.as_view(), name='password_reset_change'),
    path('profile/', CustomerProfileView.as_view(), name='customer_profile'),
    path('logout/', LogoutUserView.as_view(), name='logout_user'),
   
    
    # Flutter-optimized endpoints
    path('flutter/register/', FlutterRegisterView.as_view(), name='flutter_register'),
    path('flutter/login/', FlutterLoginView.as_view(), name='flutter_login'),
    path('flutter/logout/', FlutterLogoutView.as_view(), name='flutter_logout'),
    path('flutter/profile/', FlutterProfileView.as_view(), name='flutter_profile'),
    path('flutter/status/', flutter_user_status, name='flutter_user_status'),
    path('flutter/check-username/', flutter_check_username, name='flutter_check_username'),
    path('flutter/check-email/', flutter_check_email, name='flutter_check_email'),
    
    # JWT Token endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Enhanced location listing endpoints with complete services
    path('locations/', UserAvailableLocationsView.as_view(), name='user_available_locations'),
    path('locations/services/', location_services_list, name='all_location_services'),
    path('locations/<int:location_id>/services/', location_services_list, name='location_specific_services'),
    
    # Loyalty Points endpoints
    path('loyalty/dashboard/', LoyaltyPointsDashboardView.as_view(), name='loyalty_dashboard'),
    path('loyalty/history/', LoyaltyPointsHistoryView.as_view(), name='loyalty_history'),
    path('loyalty/redeem/', redeem_loyalty_points, name='redeem_loyalty_points'),
    path('loyalty/tier-info/', loyalty_tier_info, name='loyalty_tier_info'),
  #  path('locations/nearby/', NearbyLocationsView.as_view(), name='nearby_locations'),
 #  path('locations/popular/', PopularLocationsView.as_view(), name='popular_locations'),
   #path('locations/search/', search_locations, name='search_locations'),
    #path('locations/<int:location_id>/', location_details, name='location_details'),
    
    
    path('favorites/add/', AddFavoriteView.as_view(), name='add-favorite'),
    path('favorites/remove/', RemoveFavoriteView.as_view(), name='remove-favorite'),
    path('favorites/', ListFavoritesView.as_view(), name='list-favorites'),
]
