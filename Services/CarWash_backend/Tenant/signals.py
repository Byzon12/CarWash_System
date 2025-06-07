from .models import TenantProfile,Tenant
from django.db.models.signals import post_save

from django.dispatch import receiver

@receiver(post_save,sender=Tenant)
def create_tenant_profile(sender, instance,created,**kwargs):
    if created:
        TenantProfile.objects.create(
            tenant=instance,
            username=f"{instance.name}_{instance.id}",
            business_name=instance.name,
            business_email=f"{instance.contact_email.split('@')[0]}@tenant.com",
            phone_number=instance.contact_phone
        )
