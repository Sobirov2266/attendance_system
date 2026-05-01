from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from ..devices.models import Device
from ..groups.models import Group
from ..user_management.models import UserProfile



@login_required
def dashboard(request):
    devices = Device.objects.all()

    # Hozircha Group, Room, Attendance modellar tayyor bo'lgandan keyin
    # quyidagi 0 larni o'zgartiring:
    # group_count = Group.objects.count()
    # room_count = Room.objects.count()
    # today_attendance = Attendance.objects.filter(date=today).order_by('-timestamp')[:10]

    context = {
        'device_count':    devices.count(),
        'online_devices':  devices.filter(is_active=True).count(),
        'user_count':      UserProfile.objects.count(),
        'group_count':     Group.objects.count(),
        'room_count':      0,   # ← Room model tayyor bo'lganda o'zgartiring
        'devices':         devices[:5],
        'today_attendance': [],  # ← Attendance model tayyor bo'lganda o'zgartiring
    }
    return render(request, 'dashboard.html', context)
