from django.urls import path

from . import views

app_name = 'groups'

urlpatterns = [
    path('', views.group_list, name='group_list'),
    path('import/template/', views.download_group_template, name='download_group_template'),
    path('import/', views.import_groups, name='import_groups'),
    path('<int:group_pk>/students/', views.group_students, name='group_students'),
    path('<int:group_pk>/update/', views.update_group, name='update_group'),
    path('<int:group_pk>/toggle/', views.toggle_group_status, name='toggle_group_status'),
    path('<int:group_pk>/delete/', views.delete_group, name='delete_group'),
    path('memberships/<int:membership_pk>/toggle/', views.toggle_group_student, name='toggle_group_student'),
    path('memberships/<int:membership_pk>/delete/', views.delete_group_student, name='delete_group_student'),
]
