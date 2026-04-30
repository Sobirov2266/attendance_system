from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('device', include('apps.devices.urls')),
    path('user/', include('apps.user_management.urls')),

]
