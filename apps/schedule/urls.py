from django.urls import path

from . import views

app_name = 'schedule'

urlpatterns = [
    path('group-subjects/', views.group_subject_list, name='group_subject_list'),
    path('group-subjects/<int:pk>/update/', views.update_group_subject, name='update_group_subject'),
    path('group-subjects/<int:pk>/toggle/', views.toggle_group_subject, name='toggle_group_subject'),
    path('group-subjects/<int:pk>/delete/', views.delete_group_subject, name='delete_group_subject'),
    path('lesson-slots/', views.lesson_slot_list, name='lesson_slot_list'),
    path('lesson-slots/<int:pk>/update/', views.update_lesson_slot, name='update_lesson_slot'),
    path('lesson-slots/<int:pk>/toggle/', views.toggle_lesson_slot, name='toggle_lesson_slot'),
    path('lesson-slots/<int:pk>/delete/', views.delete_lesson_slot, name='delete_lesson_slot'),
]
