from django.contrib import admin

from .models import Group, GroupStudent


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('group_id', 'group_name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('group_id', 'group_name')
    readonly_fields = ('created_at',)


@admin.register(GroupStudent)
class GroupStudentAdmin(admin.ModelAdmin):
    list_display = ('group', 'student', 'is_active', 'joined_at')
    list_filter = ('group', 'is_active')
    search_fields = (
        'group__group_id',
        'group__group_name',
        'student__last_name',
        'student__first_name',
        'student__face_id',
        'student__ais_id',
    )
    readonly_fields = ('joined_at',)
