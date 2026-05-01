from django.urls import path
from . import views

app_name = 'devices'

urlpatterns = [
    path('list/', views.device_list, name='device_list'),                 # /devices/list/
    path('<int:device_id>/toggle/', views.toggle_device, name='toggle'),  # /devices/1/toggle/
    path('<int:device_id>/delete/', views.delete_device, name='delete'),  # /devices/1/delete/
]