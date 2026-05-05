from django.urls import path

from . import views

app_name = 'rooms'

urlpatterns = [
    path('', views.room_list, name='room_list'),
    path('import/template/', views.download_room_template, name='download_room_template'),
    path('import/', views.import_rooms, name='import_rooms'),
    path('<int:room_pk>/update/', views.update_room, name='update_room'),
    path('<int:room_pk>/toggle/', views.toggle_room_status, name='toggle_room_status'),
    path('<int:room_pk>/delete/', views.delete_room, name='delete_room'),
]
