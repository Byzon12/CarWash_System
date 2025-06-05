from .models import TenantProfile,Tenant
from django.db.models.signals import post_save

from django.dispatch import receiver

@receiver(post_save,sender=Tenant)
def create_tenant_profile(sender, instance,created,**kwargs):
    if created:
        TenantProfile.objects.create(
            tenant=instance,
            username=f"{instance.name.lower().replace(' ', '_')}_admin"
        )
