from django.urls import path
from . import views

app_name = 'devices'

urlpatterns = [
    path('device/', views.device_list, name='device_list'),
    path('toggle/<int:device_id>/', views.toggle_device, name='toggle_device'),
    path('delete/<int:device_id>/', views.delete_device, name='delete_device'),
]