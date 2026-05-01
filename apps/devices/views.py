from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Device
from .services.hikvision import check_device_connection


@login_required
def device_list(request):
    devices = Device.objects.all()
    error = None

    if request.method == "POST":
        name        = request.POST.get("name")
        ip          = request.POST.get("ip_address")
        username    = request.POST.get("username")
        password    = request.POST.get("password")
        device_type = request.POST.get("device_type")

        try:
            is_connected, error_msg = check_device_connection(ip, username, password)

            if not is_connected:
                error = error_msg or "Qurilmaga ulanib bo'lmadi."
            else:
                device = Device(
                    name=name,
                    ip_address=ip,
                    username=username,
                    device_type=device_type
                )
                device.set_password(password)
                device.save()
                return redirect('devices:device_list')

        except IntegrityError:
            error = "Bu qurilma allaqachon mavjud!"

    return render(request, 'devices/devices_list.html', {
        "devices": devices,
        "error": error
    })


@require_POST
def toggle_device(request, device_id):
    try:
        device = Device.objects.get(id=device_id)
        device.is_active = not device.is_active
        device.save()
        return JsonResponse({"success": True, "is_active": device.is_active})
    except Device.DoesNotExist:
        return JsonResponse({"success": False}, status=404)


@require_POST
def delete_device(request, device_id):
    try:
        device = Device.objects.get(id=device_id)
        device.delete()
        return JsonResponse({"success": True})
    except Device.DoesNotExist:
        return JsonResponse({"success": False}, status=404)