from django.conf import settings
from .models import TenantProfile
from django.core.mail import EmailMessage
from django.core.mail import send_mail

def send_email(subject, message, recipient_list):
    from_email = settings.DEFAULT_FROM_EMAIL
    send_mail(subject, message, from_email, recipient_list)


def send_tenant_welcome_email(tenant_profile):
    subject = "🎉 Welcome to Car Wash Manager"
    message = f"""
Hello {tenant_profile.tenant.name},

Welcome aboard! Your business "{tenant_profile.business_name}" has been successfully registered with Car Wash Manager.

You can now log in and start managing your services.

Best regards,  
Car Wash Manager Team
    """
    recipients = [
        tenant_profile.business_email,
        tenant_profile.tenant.contact_email  # assuming this is the personal email
    ]
    send_email(subject, message, recipients)

#method to send tenant profile update email

def send_tenant_profile_update_email(tenant_profile):
    subject = "🔄 Your Tenant Profile has been Updated"
    message = f"""Hello {tenant_profile.tenant.name},
Your tenant profile has been successfully updated. Here are the details:
Business Name: {tenant_profile.business_name}
Business Email: {tenant_profile.business_email}
If you did not make this change, please contact support immediately.
Best regards,
Car Wash Manager Team
    """
    recipients = [
        tenant_profile.business_email,
        tenant_profile.tenant.contact_email  # assuming this is the personal email
    ]
    send_email(subject, message, recipients)