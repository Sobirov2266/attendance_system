from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('login/',  auth_views.LoginView.as_view(
        template_name='registration/login.html'
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Bosh sahifa → core app (dashboard)
    path('', include('apps.core.urls')),

    # Qolgan app lar
    path('devices/', include('apps.devices.urls')),
    path('users/',   include('apps.user_management.urls')),
]