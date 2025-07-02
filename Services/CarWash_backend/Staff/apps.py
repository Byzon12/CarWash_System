from django.apps import AppConfig


class StaffConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Staff'
    
    def ready(self):
        # Import signal handlers to ensure they are registered
        import Staff.signals
