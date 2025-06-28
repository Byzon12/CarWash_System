from django.db.models.signals import post_save, post_delete, pre_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .utils.audit import log_audit_action
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from .models import CustomerProfile, AuditLog
from .email import send_registration_email

@receiver(post_save, sender=User)
def create_customer_profile(sender, instance, created, **kwargs):
    """
    Create a CustomerProfile instance when a User is created.
    """
    if created:
        CustomerProfile.objects.create(user=instance)
    # send registration email
    send_registration_email(instance)

@receiver(post_save, sender=CustomerProfile)
def log_profile_creation(sender, instance, created, **kwargs):
    """
    Log profile creation action.
    """
    if created:
        log_audit_action(
            None,
            
            'create_profile',
            details={'user_id': instance.user.id},
            success=True
        )  
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    Log user login action.
    """
    log_audit_action(request, 'login', details={'user_id': user.id}, success=True)
    
@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """
    Log user logout action.
    """
    log_audit_action(request, 'logout', details={'user_id': user.id}, success=True)
    
@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, **kwargs):
    """
    Log user login failed action.
    """
    log_audit_action(None, 'login_failed', details={'credentials': credentials}, success=False)

@receiver(pre_save, sender=CustomerProfile)
def log_profile_update(sender, instance, **kwargs):
    """
    Log profile update action before saving the CustomerProfile.
    """
    if instance.pk: # Check if the instance already exists (i.e., it's an update)
        original_instance = CustomerProfile.objects.get(pk=instance.pk)
        if original_instance != instance:
            log_audit_action(
                None,
                'update_profile',
                details={
                    'user_id': instance.user.id,
                    'changes': {
                        'first_name': (original_instance.first_name, instance.first_name),
                        'last_name': (original_instance.last_name, instance.last_name),
                        'email': (original_instance.email, instance.email),
                        'phone_number': (original_instance.phone_number, instance.phone_number),
                        'address': (original_instance.address, instance.address)
                    }
                },
                success=True
            )