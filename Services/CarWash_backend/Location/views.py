from multiprocessing import AuthenticationError
from django.shortcuts import render
from ast import Is
from tkinter import E
from .serializer import LocationSerializer, LocationUpdateSerializer, ServiceSerializer, LocationServiceSerializer
from django.utils.translation import gettext_lazy as _
from django.forms import ValidationError
from rest_framework import generics, permissions, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from .models import Tenant, Location, Service, LocationService
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken,TokenError  # This import is used to generate JWT tokens for user authentication


#view to handle Location creation based on tenant
class LocationCreateView(generics.CreateAPIView):
    """
    API view to create a new location for a tenant.
    """
    permission_classes = [AllowAny]  # Allow any user to create a location
    serializer_class = LocationSerializer
    queryset = Location.objects.all()
    def get_object(self):
        """to get the tenant from the header
        tenant_id = self.request.headers.get('Tenant-ID')
        if not tenant_id:
            raise ValidationError(_("Tenant-ID header is required."))
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            raise ValidationError(_("Tenant with this ID does not exist."))
        return tenant"""
    def create(self, request, *args, **kwargs):
        """        Handle the creation of a new location.
        """ 
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=201, headers=headers)
        
    #view to handle Location update based on tenant
class LocationUpdateView(generics.UpdateAPIView):
    """ API view to update an existing location for a tenant.
    """
    permission_classes = [AllowAny]  # Only authenticated users can update a location
    serializer_class = LocationUpdateSerializer
    queryset = Location.objects.all()

    def get_object(self):
        """Get the location object based on the provided ID."""
        location_id = self.kwargs.get('pk')
        try:
            return Location.objects.get(id=location_id)
        except Location.DoesNotExist:
            raise serializers.ValidationError(_("Location with this ID does not exist."))

    def update(self, request, *args, **kwargs):
        """Handle the update of an existing location."""
        instance = self.tenant = self.request.headers.get('Tenant-ID')
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    #view to handle Location deletion based on tenant
class LocationDeleteView(generics.DestroyAPIView):
    
    permission_classes = [AllowAny]  # Only authenticated users can delete a location
    """API view to delete an existing location for a tenant.
    """
    
    def get_object(self):
        """Get the location object based on the provided ID."""
        pk=self.kwargs.get('pk')
        tenant_id = self.request.headers.get('Tenant-ID')
        if not tenant_id:
            raise serializers.ValidationError(_("Tenant-ID header is required."))
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            raise serializers.ValidationError(_("Tenant with this ID does not exist."))
        try:
            return Location.objects.get(id=pk, tenant=tenant)
        except Location.DoesNotExist:
            raise serializers.ValidationError(_("Location with this ID does not exist for this tenant."))
    def delete(self, request, *args, **kwargs):
        """Handle the deletion of an existing location."""
        instance = self.get_object()
        if not instance:
            return Response({'details': 'Location not found.'}, status=404)
        self.perform_destroy(instance)
        return Response({'details': 'Location deleted successfully.'}, status=204)
    
    
#class to handle the creation of a service
class ServiceCreateView(generics.CreateAPIView):
    """
    API view to create a new service.
    """
    permission_classes = [AllowAny]  # Allow any user to create a service
    serializer_class = ServiceSerializer
    queryset = Service.objects.all()

    def create(self, request, *args, **kwargs):
        """Handle the creation of a new service."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=201, headers=headers)
    
#class to handle the update of a service
class ServiceUpdateView(generics.UpdateAPIView):
    """
    API view to update an existing service.
    """
    permission_classes = [AllowAny]  # Only authenticated users can update a service
    serializer_class = ServiceSerializer
    queryset = Service.objects.all()

    def get_object(self):
        """Get the service object based on the provided ID."""
        service_id = self.kwargs.get('pk')
        try:
            return Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            raise serializers.ValidationError(_("Service with this ID does not exist."))

    def update(self, request, *args, **kwargs):
        """Handle the update of an existing service."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    
    #class to handle the deletion of services

class ServiceDeleteView(generics.DestroyAPIView):

    """
    API view to delete an existing service.
    """
    permission_classes = [AllowAny]  # Only authenticated users can delete a service

    def get_object(self):
        """Get the service object based on the provided ID."""
        service_id = self.kwargs.get('pk')
        try:
            return Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            raise serializers.ValidationError(_("Service with this ID does not exist."))

    def delete(self, request, *args, **kwargs):
        """Handle the deletion of an existing service."""
        instance = self.get_object()
        if not instance:
            return Response({'details': 'Service not found.'}, status=404)
        self.perform_destroy(instance)
        return Response({'details': 'Service deleted successfully.'}, status=204)
        
#class to handle the creation of a location service package
class LocationServiceCreateView(generics.CreateAPIView):
    """
    API view to create a new location service package.
    """
    permission_classes = [AllowAny]  # Allow any user to create a location service package
    serializer_class = LocationServiceSerializer
    queryset = LocationService.objects.all()

    def create(self, request, *args, **kwargs):
        """Handle the creation of a new location service package."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=201, headers=headers)

#class to handle the deletion of a location service package
class LocationServiceDeleteView(generics.DestroyAPIView):
    """
    API view to delete an existing location service package.
    """
    permission_classes = [AllowAny]  # Only authenticated users can delete a location service package

    def get_object(self):
        """Get the location service package object based on the provided ID."""
        pk = self.kwargs.get('pk')
        try:
            return LocationService.objects.get(id=pk)
        except LocationService.DoesNotExist:
            raise serializers.ValidationError(_("Location Service Package with this ID does not exist."))

    def delete(self, request, *args, **kwargs):
        """Handle the deletion of an existing location service package."""
        instance = self.get_object()
        if not instance:
            return Response({'details': 'Location Service Package not found.'}, status=404)
        self.perform_destroy(instance)
        return Response({'details': 'Location Service Package deleted successfully.'}, status=204)
    
    
#class list all the location services
class LocationServiceListView(generics.ListAPIView):
    """
    API view to list all location service packages.
    """
    permission_classes = [AllowAny]  # Allow any user to view location service packages
    serializer_class = LocationServiceSerializer
    queryset = LocationService.objects.all()
    
    """
    def get_queryset(self):
        Override to filter location services by tenant
        tenant_id = self.request.headers.get('Tenant-ID')
        if not tenant_id:
            raise serializers.ValidationError(_("Tenant-ID header is required."))
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            raise serializers.ValidationError(_("Tenant with this ID does not exist."))
        return LocationService.objects.filter(location__tenant=tenant)"""
        
#class to handle retrieving/update  of a specific location service package
class LocationServiceDetailView(generics.RetrieveUpdateAPIView):
    """
    API view to retrieve and update a specific location service package.
    """
    permission_classes = [AllowAny]  # Allow any user to view and update location service packages
    serializer_class = LocationServiceSerializer
    queryset = LocationService.objects.all()

    def get_object(self):
        """Get the location service package object based on the provided ID."""
        pk = self.kwargs.get('pk')
        try:
            return LocationService.objects.get(id=pk)
        except LocationService.DoesNotExist:
            raise serializers.ValidationError(_("Location Service Package with this ID does not exist."))
    def retrieve(self, request, *args, **kwargs):
        """Handle the retrieval of a specific location service package."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """Handle the update of a specific location service package."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
#class to handle the retrieval of all locations for a tenant
