from django.shortcuts import render
from django.forms import ValidationError
from rest_framework import generics, permissions, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from .serializer import TenantProfileSerializer
from .models import Tenant


# TenantProfile views
class TenantProfileListCreateView(generics.ListCreateAPIView):
    """
    View to list and create tenant profiles.
    """
    queryset = Tenant.objects.all()
    serializer_class = TenantProfileSerializer
    permission_classes = [IsAuthenticated | AllowAny]

    def perform_create(self, serializer):
        """
        Save the new tenant profile instance.
        """
        serializer.save(user=self.request.user)