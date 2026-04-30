from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Django admin panelidagi UserProfile konfiguratsiyasi
    """
    list_display = ('get_full_name', 'username', 'position', 'is_active', 'created_at')
    list_filter = ('position', 'is_active', 'created_at')
    search_fields = ('first_name', 'last_name', 'user__username', 'user__email')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Asosiy Ma\'lumotlar', {
            'fields': ('user', 'first_name', 'last_name')
        }),
        ('Lavozim va Holat', {
            'fields': ('position', 'is_active')
        }),
        ('Vaqt Ma\'lumotlari', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    get_full_name.short_description = 'To\'liq Ismi'

    def username(self, obj):
        return obj.user.username

    username.short_description = 'Foydalanuvchi Nomi'