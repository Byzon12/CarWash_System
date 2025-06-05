from Users.models import AuditLog
from django.utils import timezone
from django.contrib.auth.models import User

def log_audit_action(request, action, details=None, success=True):
    """
    Log an audit action for a user.
    
    :param request: The HTTP request object.
    :param action: The action being logged (e.g., 'register', 'login', etc.).
    :param details: Additional details about the action (optional).
    :param success: Whether the action was successful (default is True).
    """
  
    ip_address = request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    user =getattr(request, 'user', None)  # Get the user from the request, if available

    AuditLog.objects.create(
        user = request.user if request.user.is_authenticated else None,  # Use request.user if available, otherwise None
        # If the user is not authenticated, we set user to None
        action=action,
        timestamp=timezone.now(),
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success
    )