from django.contrib import admin
from  . import models
@admin.register(models.User)
class UserAdmin(admin.ModelAdmin):
 list_display = ('username', 'email', 'full_name', 'role', 'is_active', 'is_staff', 'date_joined')
 list_filter =('role', 'is_active', 'is_staff')
 search_fields = ('username', 'email', 'full_name')
 list_per_page = 20
 ordering = ('-date_joined', 'username',)
fieldsets = (
     (None, {
         'fields': ('username', 'email', 'full_name', 'role', 'is_active', 'is_staff')
     }),
     ('Permissions', {
         'fields': ('is_superuser',)
     }),
     ('Important dates', {
         'fields': ('date_joined',)
     }),
)

add_fieldsets = (
    (None, {
        'classes': ('wide',),
        'fields': ('username', 'email', 'full_name', 'role', 'password1', 'password2', 'is_active', 'is_staff')
    }),
)
# Register your models here.
