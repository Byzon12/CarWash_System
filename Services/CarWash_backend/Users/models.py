from django.db import models
from django.contrib.auth.models import User

#creating cutomer profile model
class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,related_name='Customer_profile')
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(max_length=254, blank=True, null=True)
    
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    loyalty_points = models.PositiveIntegerField(default=0)
    updated_at= models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    

    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    class Meta:
        verbose_name = 'Customer Profile'
        verbose_name_plural = 'Customer Profiles'
        
        
        
        # this model is used to store user audit logs
class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('register', 'register user'),
        ('login', 'login user'),
        ('logout', 'logout user'),
        ('login_failed', 'login failed'),
        ('update_profile', 'update profile'),
        ('delete_account', 'delete account'),
        ('reset_password', 'reset password'),
        ('change_password', 'change password'),
        
        ('other', 'other'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    success = models.BooleanField(default=False)  # Default to False, set True on success

    def __str__(self):
        if self.user and self.user.username:
            username = self.user.username
        else:
            username = 'Anonymous'
        return f"{username} - {self.action} at {self.timestamp} (Success: {self.success})"

    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-timestamp']