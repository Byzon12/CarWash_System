from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Tenant, TenantProfile
from .email import send_tenant_welcome_email

@receiver(post_save, sender=Tenant)
def create_tenant_profile_and_send_email(sender, instance, created, **kwargs):
    if created:
        tenant_profile = TenantProfile.objects.create(
            tenant=instance,
            username=f"{instance.name.replace(' ', '')}_{instance.id}",  # no spaces
            business_name=instance.name,
            
            business_email=f"{instance.contact_email.split('@')[0]}@tenant.com",
            phone_number=instance.contact_phone
        )

        # Send welcome email immediately
        send_tenant_welcome_email(tenant_profile)
