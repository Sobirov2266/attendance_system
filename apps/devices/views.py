from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.rooms.models import Room

from .models import Device
from .services.hikvision import check_device_connection


@login_required
def device_list(request):
    devices = Device.objects.select_related('room').all()
    occupied_room_ids = Device.objects.filter(room__isnull=False).values_list(
        'room_id', flat=True
    )
    available_rooms = Room.objects.filter(is_active=True).exclude(
        pk__in=occupied_room_ids
    )
    error = None

    if request.method == "POST":
        name        = request.POST.get("name")
        ip          = request.POST.get("ip_address")
        username    = request.POST.get("username")
        password    = request.POST.get("password")
        device_type = request.POST.get("device_type")
        room_id     = request.POST.get("room")

        room = None
        if device_type == 'room' and room_id:
            room = get_object_or_404(Room, pk=room_id, is_active=True)

        try:
            is_connected, error_msg = check_device_connection(ip, username, password)

            if not is_connected:
                error = error_msg or "Qurilmaga ulanib bo'lmadi."
            else:
                device = Device(
                    name=name,
                    ip_address=ip,
                    username=username,
                    device_type=device_type,
                    room=room,
                )
                device.set_password(password)
                device.save()
                return redirect('devices:device_list')

        except IntegrityError:
            error = "Bu qurilma yoki xona allaqachon band!"
        except ValidationError as exc:
            if hasattr(exc, 'error_dict'):
                flat = []
                for errs in exc.error_dict.values():
                    flat.extend(errs)
                error = flat[0] if flat else str(exc)
            else:
                error = exc.messages[0] if exc.messages else str(exc)

    return render(request, 'devices/devices_list.html', {
        "devices": devices,
        "available_rooms": available_rooms,
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