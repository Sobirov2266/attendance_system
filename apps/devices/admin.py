from django.contrib import admin
from .models import Device, DeviceLog


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip_address', 'device_type', 'room', 'is_active', 'created_at')
    list_filter = ('device_type', 'is_active', 'created_at')
    search_fields = ('name', 'ip_address', 'room__room_name')


@admin.register(DeviceLog)
class DeviceLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'device', 'direction', 'timestamp')
    list_filter = ('direction', 'timestamp', 'device')
    search_fields = ('user__first_name', 'user__last_name', 'user__user_id', 'device__name')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)