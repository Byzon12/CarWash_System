from ast import Is
from tkinter import E
from django.shortcuts import render
from django.forms import ValidationError
from rest_framework import generics, permissions, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from .models import Employee, Tenant, TenantProfile
from .serializer import TenantProfileSerializer, TenantLoginSerializer, CreateEmpoyeeSerializer
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
            'access': str(refresh.access_token),
            'tenant': serializer.get_tenant_profile()
        })
# this to handle tenant logout
class TenantLogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):

        try:
            # Attempt to blacklist the token
            RefreshToken.for_user(request.user).blacklist()
            return Response({'detail': _('Successfully logged out.')}, status=200)
        except TokenError:
            return Response({'detail': _('Token is already blacklisted or invalid.')}, status=400)


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

 # api view to handle employee creation
 
class CreateEmployeeView(generics.CreateAPIView):
    serializer_class = CreateEmpoyeeSerializer
    permission_classes= [AllowAny]  # Allow any user to create an employee, you can change this to IsAuthenticated if you want to restrict access
     # method to create an employee

    def post(self, request):
        serializers= self.get_serializer(data= request.data)
        serializers.is_valid(raise_exception=True)
        serializers.save()
        return Response(serializers.data, status=201)

#class to list all employees of a tenant
class ListEmployeeView(generics.ListAPIView):
    queryset = Employee.objects.all()
    serializer_class = CreateEmpoyeeSerializer
    permission_classes = [AllowAny]  # Allow any user to list employees, you can change this to IsAuthenticated if you want to restrict access

    