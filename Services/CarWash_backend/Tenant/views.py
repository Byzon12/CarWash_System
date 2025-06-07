from ast import Is
from django.shortcuts import render
from django.forms import ValidationError
from rest_framework import generics, permissions, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from .models import Tenant, TenantProfile
from .serializer import TenantProfileSerializer, TenantLoginSerializer
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken,TokenError  # This import is used to generate JWT tokens for user authentication


#api view to handle tenant login with the username and password
class TenantLoginView(generics.GenericAPIView):
    serializer_class = TenantLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
      
        tenant = serializer.get_tenant()
      
        refresh = RefreshToken.for_user(tenant)
        return Response({
            'token': str(refresh),
            'tenant': serializer.get_tenant_profile(),
            'access': str(refresh.access_token)
        })

# Api view to handle tenant profile creation, update and retrieval



class TenantProfileView(generics.RetrieveUpdateAPIView):
    """_summary_

    this view handles the retrival , update and creation of tenant profile.
    """
    
  
    serializer_class = TenantProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        #only allow the tenant to access their own profile
         tenant = self.request.tenant if hasattr(self.request, 'tenant') else None
         return TenantProfile.objects.filter(tenant=tenant)
     
     # method to return the exting  tenant profile or  raise an error if it does not exist
    def get_object(self):
        queryset = self.get_queryset()
        return queryset.first()# assuming there is only one profile per tenant
    def perform_update(self, serializer):
        """Override the perform_update method to set the tenant."""
        tenant = self.request.tenant if hasattr(self.request, 'tenant') else None
        if not tenant:
            raise ValidationError(_('Tenant must be set.'))
        serializer.save(tenant=tenant)