from django.contrib import admin

from .models import Subject


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('subject_id', 'subject_name', 'is_active', 'created_at')
    search_fields = ('subject_id', 'subject_name')
