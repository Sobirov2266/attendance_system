from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display   = ('last_name', 'first_name', 'role', 'face_id', 'ais_id', 'created_at')
    list_filter    = ('role',)
    search_fields  = ('last_name', 'first_name', 'face_id', 'ais_id')
    readonly_fields = ('created_at',)