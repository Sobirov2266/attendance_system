from django.urls import path
from . import views

app_name = 'user_management'

urlpatterns = [
    path('', views.user_list, name='user_list'),                            # /users/
    path('<int:user_id>/update/', views.update_user, name='update_user'),   # /users/1/update/
    path('<int:user_id>/toggle/', views.toggle_user_status, name='toggle_user_status'),
    path('<int:user_id>/delete/', views.delete_user, name='delete_user'),   # /users/1/delete/
]
