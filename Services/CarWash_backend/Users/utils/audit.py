from datetime import datetime

def log_audit_action(request, user, action, details=None, success=True):
    from Users.models import AuditLog  # local import to avoid circular import
    ip_address = request.META.get('REMOTE_ADDR') if request else '0.0.0.0'
    user_agent = request.META.get('HTTP_USER_AGENT', 'N/A') if request else 'N/A'

    AuditLog.objects.create(
        user=user,
        action=action,
        success=success,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
        timestamp=datetime.now()
    )
