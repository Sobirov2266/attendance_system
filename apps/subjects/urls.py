from django.urls import path

from . import views

app_name = 'subjects'

urlpatterns = [
    path('', views.subject_list, name='subject_list'),
    path('import/template/', views.download_subject_template, name='download_subject_template'),
    path('import/', views.import_subjects, name='import_subjects'),
    path('<int:subject_pk>/update/', views.update_subject, name='update_subject'),
    path('<int:subject_pk>/toggle/', views.toggle_subject_status, name='toggle_subject_status'),
    path('<int:subject_pk>/delete/', views.delete_subject, name='delete_subject'),
]
