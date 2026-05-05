from django.contrib import admin

from .models import GroupSubject, LessonSlot


@admin.register(GroupSubject)
class GroupSubjectAdmin(admin.ModelAdmin):
    list_display = ('group', 'subject', 'teacher', 'is_active', 'created_at')
    list_filter = ('is_active', 'group', 'subject')
    search_fields = (
        'group__group_name',
        'subject__subject_name',
        'teacher__last_name',
        'teacher__first_name',
    )


@admin.register(LessonSlot)
class LessonSlotAdmin(admin.ModelAdmin):
    list_display = (
        'group_subject',
        'room',
        'weekday',
        'lesson_number',
        'start_time',
        'end_time',
        'is_active',
    )
    list_filter = ('is_active', 'weekday', 'lesson_number', 'room', 'group_subject__group')
    search_fields = (
        'group_subject__group__group_name',
        'group_subject__subject__subject_name',
        'room__room_name',
    )
