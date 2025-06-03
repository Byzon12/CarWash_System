from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Users'
    
    def ready(self):
        # Import signal handlers to ensure they are registered
        import Users.signal
