from django.urls import path
from . import views


app_name = 'user_management'

urlpatterns = [
    # Foydalanuvchilar ro'yxati
    path('users/', views.user_list, name='user_list'),

    # Yangi foydalanuvchi qo'shish
    path('users/add/', views.user_create, name='user_create'),

    # Foydalanuvchi tahrirlash
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),

    # Foydalanuvchi o'chirish
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),

    # Foydalanuvchi tafsilotlari
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),

    # Kendi profili
    path('profile/me/', views.my_profile, name='my_profile'),
]