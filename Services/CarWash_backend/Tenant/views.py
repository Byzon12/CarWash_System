from django.shortcuts import render
from django.forms import ValidationError
from rest_framework import generics, permissions, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from .models import Tenant, TenantProfile
from .serializer import TenantprofileSerializer
from django.utils.translation import gettext_lazy as _

# Api view to handle tenant profile creation, update and retrieval

class TenantProfileView(generics.RetrieveUpdateAPIView):
    """_summary_

    this view handles the retrival , update and creation of tenant profile.
    """
    
  
    serializer_class = TenantprofileSerializer
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