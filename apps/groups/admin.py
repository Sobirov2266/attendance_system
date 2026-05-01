from django.contrib import admin

from .models import Group


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('group_id', 'group_name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('group_id', 'group_name')
    readonly_fields = ('created_at',)
