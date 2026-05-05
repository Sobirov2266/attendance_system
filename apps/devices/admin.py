from django.contrib import admin
from .models import Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip_address', 'device_type', 'room', 'is_active', 'created_at')
    list_filter = ('device_type', 'is_active')
    search_fields = ('name', 'ip_address', 'room__room_name')