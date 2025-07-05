from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

from Staff.models import StaffProfile, Staff



@receiver(post_save, sender=Staff)
def create_staff_profile(sender, instance, created, **kwargs):
    if created:
        # Create the auth user
        StaffProfile.objects.create(
            tenant=instance.tenant,
            staff=instance,
            location=instance.location,
            username=instance.username,
            work_email=instance.email,
            role=instance.role,
            email=instance.email
        
        )
