from ast import Is
from tkinter import E
import token
from urllib import request
from django.shortcuts import render
from django.forms import ValidationError
from rest_framework import generics, permissions, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from .models import Tenant, TenantProfile, Task
from .serializer import TenantProfileSerializer, TenantLoginSerializer, EmployeeRoleSalarySerializer, CreateEmployeeSerializer, TaskSerializer
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken,TokenError  # This import is used to generate JWT tokens for user authentication
from .email import send_tenant_profile_update_email
from Location.models import Location, Service, LocationService
from Staff.models import StaffProfile, StaffRole

#api view to handle tenant login with the username and password
class TenantLoginView(generics.GenericAPIView):
    serializer_class = TenantLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
      
        tenant = serializer.get_tenant()
        refresh = RefreshToken()
        refresh['user_id'] = str(tenant.id)  # Set the user ID in the refresh token
        return Response({
            'token': str(refresh),
            'access': str(refresh.access_token),
            'tenant': serializer.get_tenant_profile()
        })
# this to handle tenant logout
class TenantLogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'detail': _('Refresh token is required for logout.')}, status=400)

        try:
            
            token = RefreshToken(refresh_token)
            # Blacklist the token
            token.blacklist()
            return Response({'detail': _('Successfully logged out.')}, status=200)
        except TokenError:
            return Response({'detail': _('Token is already blacklisted or invalid.')}, status=400)


class TenantProfileView(generics.RetrieveUpdateAPIView):
    """_summary_

    this view handles the retrival , update and creation of tenant profile.
    """
    
  
    serializer_class = TenantProfileSerializer
    permission_classes = [IsAuthenticated]
   # queryset = TenantProfile.objects.all()  # Assuming TenantProfile has a ForeignKey to Tenant


    def get_queryset(self):
        #only allow the tenant to access their own profile
         tenant = self.request.user  #  tenant is set in the request object
         return TenantProfile.objects.filter(tenant=tenant)  # Assuming TenantProfile has a ForeignKey to Tenant

     # method to return the exting  tenant profile or  raise an error if it does not exist
    def get_object(self):
        queryset = self.get_queryset()
        return queryset.first()# assuming there is only one profile per tenant

#class to handle tenant profile retrieval and update
class TenantProfileDetailsView(generics.RetrieveUpdateAPIView):
    serializer_class = TenantProfileSerializer
    permission_classes = [IsAuthenticated]  # Only authenticated users can access this view
    # Assuming TenantProfile has a ForeignKey to Tenant
    queryset = TenantProfile.objects.all()  # Assuming TenantProfile has a ForeignKey to Tenant

    def get_object(self):
        # get tenant based on the request user
        tenant = self.request.user  # Assuming you have set the tenant in the request object
        if not tenant or not isinstance(tenant, Tenant):
            raise ValidationError( _('Tenant must be authenticated.'))
        try:
            return TenantProfile.objects.get(tenant=tenant)
        except TenantProfile.DoesNotExist:
            raise ValidationError(_('Tenant profile does not exist.'))

    # method to retrive the tenant profile details
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance:
            return Response({'detail': _('Tenant profile not found.')}, status=404) 
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    #method to update the tenant profile details
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance:
            return Response({'detail': _('Tenant profile not found.')}, status=404)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # send an email to the tenant profile email
        send_tenant_profile_update_email(instance)
        return Response(serializer.data)

# api view to handle employee creation

class CreateEmployeeView(generics.CreateAPIView):
    serializer_class = CreateEmployeeSerializer
    permission_classes= [IsAuthenticated]  # Allow only authenticated users to create an employee
     # method to create an employee

    def perform_create(self, serializer):
        tenant = self.request.user  # Assuming the user is a tenant
        serializer.save(tenant=tenant)  # Save the tenant in the employee instance

#class to list all employees of a tenant
class ListEmployeeView(generics.ListAPIView):
    serializer_class = CreateEmployeeSerializer
    permission_classes = [IsAuthenticated]  # Allow only authenticated users to list employees

    def get_queryset(self):
        tenant = self.request.user  # Assuming the user is a tenant
        return StaffProfile.objects.filter(tenant=tenant)  # Filter employees by tenant

    #view to to retrieve, create and update the salary of an employee and a sign roles
class CreateEmployeeSalaryView(generics.CreateAPIView):

    """
    This view handles the creation of employee roles and their associated salaries.
    It allows authenticated tenants to create or update employee roles and salaries.
    """
    serializer_class = EmployeeRoleSalarySerializer
    permission_classes = [IsAuthenticated]  # Allow only authenticated users to update employee salary

    def get_queryset(self):
        tenant = self.request.user  # Assuming the user is a tenant
        return StaffRole.objects.filter(tenant=tenant)  # Filter employee roles by tenant

    def perform_create(self, serializer):
        tenant = self.request.user  # Assuming the user is a tenant
        location = Location.objects.get(pk=self.request.data.get('location'))  # Get the location from the request data
        serializer.save(tenant=tenant, location=location)  # Save the tenant in the employee role instance

    #class to delete an employee

    
class DeleteEmployeeView(generics.DestroyAPIView):

    permission_classes = [IsAuthenticated]  # Allow only authenticated users to delete employees


    #method to get the employee object by primary key and tenant
    def get_object(self):
        pk = self.kwargs.get('pk')
        tenant = self.request.user  # Assuming the user is a tenant
       
        try:
            employee = StaffProfile.objects.get(pk=pk, tenant=tenant)
            return employee
        except StaffProfile.DoesNotExist:
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
        tenant = self.request.user  # Assuming the user is a tenant
        try:
            employee = StaffProfile.objects.get(pk=pk, tenant=tenant)
            return employee
        except StaffProfile.DoesNotExist:
            return None

    def delete(self, request, *args, **kwargs):
        employee = self.get_object()
        if not employee:
            return Response({'detail': _('Employee not found.')}, status=404)
        # Soft delete by setting is_active to False+++
        employee.is_active = False
        employee.save()
        return Response({'detail': _('Employee deactivated successfully.')}, status=200)
    
    
#class to handle employee activation

class ActivateEmployeeView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]  # Allow only authenticated users to activate employees

    def get_object(self):
        pk = self.kwargs.get('pk')
        tenant = self.request.user  # Assuming the user is a tenant
        try:
            employee = StaffProfile.objects.get(pk=pk, tenant=tenant)
            return employee
        except StaffProfile.DoesNotExist:
            return None

    def put(self, request, *args, **kwargs):
        employee = self.get_object()
        if not employee:
            return Response({'detail': _('Employee not found.')}, status=404)
        # Activate the employee by setting is_active to True
        employee.is_active = True
        employee.save()
        return Response({'detail': _('Employee activated successfully.')}, status=200)
    
    
#the views class handles the creation of tasks for a tenant forthe login tenant
class TaskCreateView(generics.CreateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]  # Allow only authenticated users to create tasks
    
    def get_queryset(self):
        tenant = self.request.user  # Assuming the user is a tenant
        return Task.objects.filter(tenant=tenant)  # Filter tasks by tenant

    def perform_create(self, serializer):
        tenant = self.request.user  # Assuming the user is a tenant
        serializer.save(tenant=tenant)
