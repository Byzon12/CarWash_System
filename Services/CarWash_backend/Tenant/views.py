from ast import Is
from tkinter import E
from django.shortcuts import render
from django.forms import ValidationError
from rest_framework import generics, permissions, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from .models import Employee, EmployeeRole, Tenant, TenantProfile
from .serializer import TenantProfileSerializer, TenantLoginSerializer, EmployeeRoleSalarySerializer, CreateEmployeeSerializer
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
    serializer_class = CreateEmployeeSerializer
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
    serializer_class = CreateEmployeeSerializer
    permission_classes = [AllowAny]  # Allow any user to list employees, you can change this to IsAuthenticated if you want to restrict access

    #view to update the salarya of an employee and a sign roles
class CreateEmployeeSalaryView(generics.CreateAPIView):
    
    queryset = EmployeeRole.objects.all()
    serializer_class = EmployeeRoleSalarySerializer
    permission_classes = [AllowAny]  # Allow any user to update employee salary
# method to create or update the salary of an employee
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee_role = serializer.save()
        return Response(serializer.data, status=201)
    
    #class to delete an employee """"

    
class DeleteEmployeeView(generics.DestroyAPIView):

    permission_classes = [AllowAny]  # Allow only authenticated users to delete employees


    #method to get the employee object by primary key and tenant
    def get_object(self):
        pk = self.kwargs.get('pk')
        tenant_id = self.request.headers.get('X-Tenant-ID')  # Assuming tenant ID is passed in the headers
       
        try:
            tenant= Tenant.objects.get(id=tenant_id)
            return tenant
        except Tenant.DoesNotExist: 
            employee = Employee.objects.get(pk=pk, tenant=tenant)
            return employee
        except Employee.DoesNotExist:
            return None

    # Method to delete an employee

    def delete(self, request, *args, **kwargs):
        employee = self.get_object()
        if not employee:
            return Response({'detail': _('Employee not found.')}, status=404)
        employee.delete()
        return Response({'detail': _('Employee deleted successfully.')}, status=204)

#class to soft delete employee by deactivating them

# class to deactivate employee

class DeactivateEmployeeView(generics.DestroyAPIView):
    permission_classes = [AllowAny]# Allow only authenticated users to deactivate employees
     # Assuming you want to use the same serializer for deactivation
    def get_object(self):
        pk = self.kwargs.get('pk')
        tenant_id = self.request.headers.get('X-Tenant-ID')  # Assuming tenant ID is passed in the headers
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return None
        try:
            employee = Employee.objects.get(pk=pk, tenant=tenant)
            return employee
        except Employee.DoesNotExist:
            return None

    def delete(self, request, *args, **kwargs):
        employee = self.get_object()
        if not employee:
            return Response({'detail': _('Employee not found.')}, status=404)
        # Soft delete by setting is_active to False+++
        employee.is_active = False
        employee.save()
        return Response({'detail': _('Employee deactivated successfully.')}, status=200)