from django.shortcuts import render, redirect
from .models import Device
from django.db import IntegrityError

def device_list(request):
    devices = Device.objects.all()
    error = None

    if request.method == "POST":
        name = request.POST.get("name")
        ip = request.POST.get("ip_address")
        username = request.POST.get("username")
        password = request.POST.get("password")
        device_type = request.POST.get("device_type")

        try:
            device = Device(
                name=name,
                ip_address=ip,
                username=username,
                device_type=device_type
            )
            device.set_password(password)
            device.save()

            return redirect('device_list')

        except IntegrityError:
            error = "Bu FACE ID allaqachon mavjud, tekshirib qayta kiriting !!"

    return render(request, 'devices/dashboard.html', {
        "devices": devices,
        "error": error
    })





