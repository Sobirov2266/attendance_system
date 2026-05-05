from django.urls import path

from . import views
from .models import UserProfile

app_name = 'user_management'

urlpatterns = [
    path('', views.user_list, name='user_list'),
    path('students/', views.user_list, {'role_scope': UserProfile.Role.STUDENT}, name='student_list'),
    path('students/import/template/', views.download_student_template, name='download_student_template'),
    path('students/import/', views.import_students, name='import_students'),
    path('teachers/', views.user_list, {'role_scope': UserProfile.Role.TEACHER}, name='teacher_list'),
    path('staff/', views.user_list, {'role_scope': UserProfile.Role.STAFF}, name='staff_list'),
    path('<int:user_id>/update/', views.update_user, name='update_user'),
    path('<int:user_id>/toggle/', views.toggle_user_status, name='toggle_user_status'),
    path('<int:user_id>/delete/', views.delete_user, name='delete_user'),   # /users/1/delete/
]
