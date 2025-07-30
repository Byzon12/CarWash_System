from multiprocessing import AuthenticationError
from django.shortcuts import render
from rest_framework import generics, permissions, serializers, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from .serializer import (
    LocationSerializer, LocationUpdateSerializer, ServiceSerializer, 
    LocationServiceSerializer
)
from .models import Location, Service, LocationService, Favorite
from django.db import transaction

class LocationCreateView(generics.CreateAPIView):
    """
     API view to create a new location for a tenant with comprehensive error handling.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = LocationSerializer
    
    def get_serializer_context(self):
        """Add tenant to serializer context."""
        context = super().get_serializer_context()
        context['tenant'] = self.request.user
        return context
    
    def create(self, request, *args, **kwargs):
        """Handle location creation with enhanced response format."""
        try:
            with transaction.atomic():
                serializer = self.get_serializer(data=request.data)
                if serializer.is_valid():
                    location = serializer.save()
                    return Response({
                        'success': True,
                        'message': 'Location created successfully',
                        'data': serializer.data
                    }, status=status.HTTP_201_CREATED)
                
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while creating the location',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LocationUpdateView(generics.UpdateAPIView):
    """
    API view to update an existing location for a tenant.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = LocationUpdateSerializer
    
    def get_object(self):
        """Get location object filtered by tenant."""
        location_id = self.kwargs.get('pk')
        tenant = self.request.user
        
        try:
            return Location.objects.get(id=location_id, tenant=tenant)
        except Location.DoesNotExist:
            raise serializers.ValidationError({
                'detail': _("Location not found or you don't have permission to access it")
            })
    
    def update(self, request, *args, **kwargs):
        """Handle location update with enhanced response."""
        try:
            partial = kwargs.pop('partial', True)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            
            if serializer.is_valid():
                self.perform_update(serializer)
                return Response({
                    'success': True,
                    'message': 'Location updated successfully',
                    'data': serializer.data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while updating the location',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LocationDeleteView(generics.DestroyAPIView):
    """
     API view to delete an existing location for a tenant.
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """Get location object filtered by tenant."""
        location_id = self.kwargs.get('pk')
        tenant = self.request.user
        
        try:
            return Location.objects.get(id=location_id, tenant=tenant)
        except Location.DoesNotExist:
            raise serializers.ValidationError({
                'detail': _("Location not found or you don't have permission to delete it")
            })
    
    def destroy(self, request, *args, **kwargs):
        """Handle location deletion with enhanced response."""
        try:
            instance = self.get_object()
            
            # Check if location has active services
            if instance.location_services.exists():
                return Response({
                    'success': False,
                    'message': 'Cannot delete location with active service packages',
                    'error': 'Please remove all service packages before deleting this location'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            self.perform_destroy(instance)
            return Response({
                'success': True,
                'message': 'Location deleted successfully'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while deleting the location',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#api view to handle activation of the location

class LocationActivateView(generics.DestroyAPIView):
    """
     API view to activate an existing location for a tenant.
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """Get location object filtered by tenant."""
        location_id = self.kwargs.get('pk')
        tenant = self.request.user
        
        try:
            return Location.objects.get(id=location_id, tenant=tenant)
        except Location.DoesNotExist:
            raise serializers.ValidationError({
                'detail': _("Location not found or you don't have permission to delete it")
            })
    
    def destroy(self, request, *args, **kwargs):
        """Handle location deletion with enhanced response."""
        try:
            instance = self.get_object()
            
            # Check if location has active services
            if instance.location_services.exists():
                return Response({
                    'success': False,
                    'message': 'Cannot delete location with active service packages',
                    'error': 'Please remove all service packages before deleting this location'
                }, status=status.HTTP_400_BAD_REQUEST)

            instance.is_active = True
            instance.save()
            return Response({
                'success': True,
                'message': 'Location activated successfully'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while activating the location',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class LocationListView(generics.ListAPIView):
    """
    Enhanced API view to list all locations for a tenant with pagination.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = LocationSerializer
    
    def get_queryset(self):
        """Filter locations by authenticated tenant."""
        return Location.objects.filter(tenant=self.request.user).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """Handle location listing with enhanced response."""
        try:
            queryset = self.get_queryset()
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response({
                    'success': True,
                    'message': 'Locations retrieved successfully',
                    'data': serializer.data
                })
            
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'success': True,
                'message': 'Locations retrieved successfully',
                'data': serializer.data,
                'count': queryset.count()
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while retrieving locations',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ServiceCreateView(generics.CreateAPIView):
    """
    Enhanced API view to create a new service with comprehensive validation.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ServiceSerializer
    
    def get_serializer_context(self):
        """Add tenant to serializer context."""
        context = super().get_serializer_context()
        context['tenant'] = self.request.user
        return context
    
    def create(self, request, *args, **kwargs):
        """Handle service creation with enhanced response."""
        try:
            with transaction.atomic():
                serializer = self.get_serializer(data=request.data)
                if serializer.is_valid():
                    service = serializer.save()
                    return Response({
                        'success': True,
                        'message': 'Service created successfully',
                        'data': serializer.data
                    }, status=status.HTTP_201_CREATED)
                
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while creating the service',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ServiceListView(generics.ListAPIView):
    """
    Enhanced API view to list all services for a tenant.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ServiceSerializer
    
    def get_queryset(self):
        """Filter services by authenticated tenant."""
        return Service.objects.filter(tenant=self.request.user).order_by('name')
    
    def list(self, request, *args, **kwargs):
        """Handle service listing with enhanced response."""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'success': True,
                'message': 'Services retrieved successfully',
                'data': serializer.data,
                'count': queryset.count()
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while retrieving services',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ServiceUpdateView(generics.UpdateAPIView):
    """
    Enhanced API view to update an existing service.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ServiceSerializer
    
    def get_object(self):
        """Get service object filtered by tenant."""
        service_id = self.kwargs.get('pk')
        tenant = self.request.user
        
        try:
            return Service.objects.get(id=service_id, tenant=tenant)
        except Service.DoesNotExist:
            raise serializers.ValidationError({
                'detail': _("Service not found or you don't have permission to access it")
            })
    
    def get_serializer_context(self):
        """Add tenant to serializer context."""
        context = super().get_serializer_context()
        context['tenant'] = self.request.user
        return context
    
    def update(self, request, *args, **kwargs):
        """Handle service update with enhanced response."""
        try:
            partial = kwargs.pop('partial', True)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            
            if serializer.is_valid():
                self.perform_update(serializer)
                return Response({
                    'success': True,
                    'message': 'Service updated successfully',
                    'data': serializer.data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while updating the service',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ServiceDeleteView(generics.DestroyAPIView):
    """
    Enhanced API view to delete an existing service.
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """Get service object filtered by tenant."""
        service_id = self.kwargs.get('pk')
        tenant = self.request.user
        
        try:
            return Service.objects.get(id=service_id, tenant=tenant)
        except Service.DoesNotExist:
            raise serializers.ValidationError({
                'detail': _("Service not found or you don't have permission to delete it")
            })
    
    def destroy(self, request, *args, **kwargs):
        """Handle service deletion with enhanced response."""
        try:
            instance = self.get_object()
            
            # Check if service is used in any location services
            if instance.location_services.exists():
                return Response({
                    'success': False,
                    'message': 'Cannot delete service that is used in service packages',
                    'error': f'Service is used in {instance.location_services.count()} package(s)'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            self.perform_destroy(instance)
            return Response({
                'success': True,
                'message': 'Service deleted successfully'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while deleting the service',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LocationServiceCreateView(generics.CreateAPIView):
    """
    Enhanced API view to create a new location service package.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = LocationServiceSerializer
    
    def create(self, request, *args, **kwargs):
        """Handle location service creation with enhanced response."""
        try:
            with transaction.atomic():
                serializer = self.get_serializer(data=request.data)
                if serializer.is_valid():
                    location_service = serializer.save()
                    return Response({
                        'success': True,
                        'message': 'Service package created successfully',
                        'data': serializer.data
                    }, status=status.HTTP_201_CREATED)
                
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while creating the service package',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LocationServiceListView(generics.ListAPIView):
    """
    Enhanced API view to list all location service packages.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = LocationServiceSerializer
    
    def get_queryset(self):
        """Filter location services by authenticated tenant."""
        return LocationService.objects.filter(
            location__tenant=self.request.user
        ).select_related('location').prefetch_related('service').order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """Handle location service listing with enhanced response."""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'success': True,
                'message': 'Service packages retrieved successfully',
                'data': serializer.data,
                'count': queryset.count()
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while retrieving service packages',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LocationServiceDetailView(generics.RetrieveUpdateAPIView):
    """
    Enhanced API view to retrieve and update a specific location service package.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = LocationServiceSerializer
    
    def get_object(self):
        """Get location service filtered by tenant."""
        pk = self.kwargs.get('pk')
        tenant = self.request.user
        
        try:
            return LocationService.objects.get(id=pk, location__tenant=tenant)
        except LocationService.DoesNotExist:
            raise serializers.ValidationError({
                'detail': _("Service package not found or you don't have permission to access it")
            })
    
    def retrieve(self, request, *args, **kwargs):
        """Handle service package retrieval with enhanced response."""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response({
                'success': True,
                'message': 'Service package retrieved successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while retrieving the service package',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        """Handle service package update with enhanced response."""
        try:
            partial = kwargs.pop('partial', True)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            
            if serializer.is_valid():
                self.perform_update(serializer)
                return Response({
                    'success': True,
                    'message': 'Service package updated successfully',
                    'data': serializer.data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while updating the service package',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LocationServiceDeleteView(generics.DestroyAPIView):
    """
    Enhanced API view to delete an existing location service package.
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """Get location service filtered by tenant."""
        pk = self.kwargs.get('pk')
        tenant = self.request.user
        
        try:
            return LocationService.objects.get(id=pk, location__tenant=tenant)
        except LocationService.DoesNotExist:
            raise serializers.ValidationError({
                'detail': _("Service package not found or you don't have permission to delete it")
            })
    
    def destroy(self, request, *args, **kwargs):
        """Handle service package deletion with enhanced response."""
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({
                'success': True,
                'message': 'Service package deleted successfully'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'message': 'An error occurred while deleting the service package',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import Favorite, Location
from .serializer import FavoriteSerializer

class AddFavoriteView(generics.CreateAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        location_id = request.data.get('location')
        location = Location.objects.get(id=location_id)
        favorite, created = Favorite.objects.get_or_create(user=request.user, location=location)
        if not created:
            return Response({'detail': 'Already favorited.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(favorite)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class RemoveFavoriteView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        location_id = request.data.get('location')
        favorite = Favorite.objects.filter(user=request.user, location_id=location_id).first()
        if favorite:
            favorite.delete()
            return Response({'detail': 'Removed from favorites.'}, status=status.HTTP_204_NO_CONTENT)
        return Response({'detail': 'Favorite not found.'}, status=status.HTTP_404_NOT_FOUND)

class ListFavoritesView(generics.ListAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)
