from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

# Define an inline admin descriptor for UserProfile
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user' # Explicitly set the foreign key name if not 'user'

# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role')
    list_select_related = ('profile',)

    def get_role(self, instance):
        try:
            return instance.profile.get_role_display()
        except UserProfile.DoesNotExist:
            return None
    get_role.short_description = 'Role'

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Optionally, if you want a separate admin for UserProfile (e.g., for advanced filtering or actions)
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email')

from django.contrib.gis import admin as gis_admin
from .models import Field

@admin.register(Field)
class FieldAdmin(gis_admin.GISModelAdmin):
    list_display = ('name', 'owner', 'description')
    list_filter = ('owner',)
    search_fields = ('name', 'owner__username')
    default_lat = 0 # Default latitude for the map
    default_lon = 0 # Default longitude for the map
    default_zoom = 4 # Default zoom level

from .models import Crop, OperationType, AgroOperation

@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = ('name', 'scientific_name')
    search_fields = ('name', 'scientific_name')

@admin.register(OperationType)
class OperationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(AgroOperation)
class AgroOperationAdmin(admin.ModelAdmin):
    list_display = ('field', 'crop', 'operation_type', 'operation_date', 'user_display')
    list_filter = ('field', 'crop', 'operation_type', 'operation_date', 'user')
    search_fields = ('field__name', 'crop__name', 'operation_type__name', 'description', 'user__username')
    readonly_fields = ('user', 'created_at', 'updated_at') # User is set in the view

    def user_display(self, obj):
        return obj.user.username if obj.user else "N/A"
    user_display.short_description = 'User'

    def save_model(self, request, obj, form, change):
        if not obj.pk: # If creating a new object
            obj.user = request.user
        super().save_model(request, obj, form, change)
