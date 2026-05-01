from django.urls import path
from . import views

app_name = 'user_management'

urlpatterns = [
    path('', views.user_list, name='user_list'),                          # /users/
    path('<int:user_id>/delete/', views.delete_user, name='delete_user'), # /users/1/delete/
]