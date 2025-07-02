from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

from Tenant.models import Employee
from Staff.models import StaffProfile

User = get_user_model()
"""
@receiver(post_save, sender=Employee)
@receiver(post_save, sender=Employee)

def create_staff_profile(sender, instance, created, **kwargs):
    if created:
        # Create the auth user
        StaffProfile.objects.create(
            tenant=instance.tenant,
            location=instance.location,
            username=instance.username,
            work_email=instance.work_email,
            full_name=instance.full_name,
            role=instance.role,
            phone_number=instance.phone_number,
            email=instance.email
        
        )"""
