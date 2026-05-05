from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.rooms.models import Room
from apps.user_management.models import UserProfile

from .models import Device
from .services.hikvision import check_device_connection
from .services.hikvision_real import fetch_real_attendance_logs


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


@login_required
def monitoring(request):
    """Tanlangan kun bo'yicha faqat turniket xotirasidagi loglar."""
    tashkent_tz = timezone.get_fixed_timezone(300)
    today = timezone.localtime(timezone.now(), tashkent_tz).date()
    last_10_dates = [today - timedelta(days=i) for i in range(10)]
    last_10_days = [d.strftime('%Y-%m-%d') for d in last_10_dates]

    selected_date_str = request.GET.get('date', '').strip()
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today

    if selected_date not in last_10_dates:
        selected_date = today

    day_start = timezone.make_aware(
        datetime.combine(selected_date, datetime.min.time()),
        tashkent_tz,
    )
    day_end = timezone.make_aware(
        datetime.combine(selected_date, datetime.max.time()),
        tashkent_tz,
    )

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()
        if action == 'set_role':
            employee_id = _normalize_user_identifier(request.POST.get('user_id'))
            role = request.POST.get('role', '').strip()
            full_name = (request.POST.get('full_name') or '').strip()

            if not employee_id:
                return redirect(request.get_full_path())

            if role not in UserProfile.Role.values:
                return redirect(request.get_full_path())

            first_name, last_name = _split_full_name(full_name)
            profile = UserProfile.objects.filter(
                Q(ais_id=employee_id) | Q(face_id=employee_id)
            ).first()

            if profile:
                profile.role = role
                if first_name and first_name != "Noma'lum":
                    profile.first_name = first_name
                if last_name and last_name != '-':
                    profile.last_name = last_name
                profile.save(update_fields=['role', 'first_name', 'last_name'])
            else:
                UserProfile.objects.create(
                    ais_id=employee_id,
                    face_id=employee_id,
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                    is_active=True,
                )

            return redirect(request.get_full_path())

    search_query = request.GET.get('q', '').strip()
    selected_device = request.GET.get('device', '').strip()
    role_filter = request.GET.get('role', 'all').strip()
    devices = list(Device.objects.filter(is_active=True).order_by('name'))

    target_devices = devices
    if selected_device and selected_device.isdigit():
        selected_device_id = int(selected_device)
        target_devices = [d for d in devices if d.id == selected_device_id]
    else:
        selected_device_id = None

    users, role_filter = _collect_monitoring_users(
        target_devices=target_devices,
        day_start=day_start,
        day_end=day_end,
        tashkent_tz=tashkent_tz,
        role_filter=role_filter,
        search_query=search_query,
    )

    paginator = Paginator(users, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'devices/monitoring.html', {
        'users': page_obj.object_list,
        'page_obj': page_obj,
        'total_count': paginator.count,
        'devices': devices,
        'selected_date': selected_date.strftime('%Y-%m-%d'),
        'last_10_days': last_10_days,
        'q': search_query,
        'role_filter': role_filter,
        'role_choices': UserProfile.Role.choices,
        'selected_device': str(selected_device_id) if selected_device_id else '',
        'refresh_seconds': 30,
    })


@login_required
def latest_logs(request):
    """Monitoring endpoint endi pagination bilan ishlaydi; realtime API ishlatilmaydi."""
    return JsonResponse({'logs': []})


@login_required
def monitoring_export_pdf(request):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    except ImportError:
        return HttpResponse("PDF export uchun reportlab o'rnatilmagan.", status=500)

    tashkent_tz = timezone.get_fixed_timezone(300)
    today = timezone.localtime(timezone.now(), tashkent_tz).date()
    last_10_dates = [today - timedelta(days=i) for i in range(10)]

    selected_date_str = request.GET.get('date', '').strip()
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today

    if selected_date not in last_10_dates:
        selected_date = today

    day_start = timezone.make_aware(
        datetime.combine(selected_date, datetime.min.time()),
        tashkent_tz,
    )
    day_end = timezone.make_aware(
        datetime.combine(selected_date, datetime.max.time()),
        tashkent_tz,
    )

    search_query = request.GET.get('q', '').strip()
    selected_device = request.GET.get('device', '').strip()
    role_filter = request.GET.get('role', 'all').strip()
    devices = list(Device.objects.filter(is_active=True).order_by('name'))

    target_devices = devices
    if selected_device and selected_device.isdigit():
        selected_device_id = int(selected_device)
        target_devices = [d for d in devices if d.id == selected_device_id]
    else:
        selected_device_id = None

    users, role_filter = _collect_monitoring_users(
        target_devices=target_devices,
        day_start=day_start,
        day_end=day_end,
        tashkent_tz=tashkent_tz,
        role_filter=role_filter,
        search_query=search_query,
    )

    device_name = "Barcha qurilmalar"
    if selected_device_id:
        selected_device_obj = next((d for d in devices if d.id == selected_device_id), None)
        if selected_device_obj:
            device_name = selected_device_obj.name

    filename = f"monitoring_{selected_date.strftime('%Y%m%d')}_{role_filter}.pdf"
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=8 * mm,
        leftMargin=8 * mm,
        topMargin=8 * mm,
        bottomMargin=8 * mm,
    )

    table_data = [
        [
            f"Sana: {_format_uzbek_date(selected_date)}",
            f"Qurilma: {device_name}",
            f"Qidiruv: {search_query or '-'}",
            f"Jami: {len(users)}",
        ],
        ['#', 'Ism Familya', "Oxirgi o'tish", "O'tishlar soni"],
    ]

    for index, user in enumerate(users, start=1):
        table_data.append([
            str(index),
            user['full_name'],
            _format_uzbek_datetime(timezone.localtime(user['last_seen'], tashkent_tz)),
            str(user['pass_count']),
        ])

    table = Table(
        table_data,
        colWidths=[14 * mm, 72 * mm, 64 * mm, 30 * mm],
        repeatRows=2,
    )
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTNAME', (0, 2), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e6f0ff')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 2), (1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    doc.build([table])
    return response


def _normalize_user_identifier(value):
    identifier = str(value or '').strip()
    if identifier.isdigit():
        return identifier.lstrip('0') or '0'
    return identifier


_UZ_MONTH_NAMES = (
    'yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun',
    'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr',
)


def _format_uzbek_date(value):
    return f"{value.day}-{_UZ_MONTH_NAMES[value.month - 1]}"


def _format_uzbek_datetime(value):
    return f"{_format_uzbek_date(value)} {value.strftime('%H:%M:%S')}"


def _split_full_name(full_name):
    cleaned = (full_name or '').strip()
    if not cleaned:
        return "Noma'lum", '-'
    parts = cleaned.split()
    if len(parts) == 1:
        return parts[0], '-'
    return ' '.join(parts[1:]), parts[0]


def _collect_monitoring_users(target_devices, day_start, day_end, tashkent_tz, role_filter, search_query):
    logs = _get_turnstile_logs_cached(
        target_devices=target_devices,
        day_start=day_start,
        day_end=day_end,
        tashkent_tz=tashkent_tz,
    )

    resolved_ids = {log['user_id'] for log in logs if log['user_id']}
    profiles = UserProfile.objects.filter(is_active=True).filter(
        Q(ais_id__in=resolved_ids) | Q(face_id__in=resolved_ids)
    )
    profiles_by_id = {}
    for profile in profiles:
        profiles_by_id[_normalize_user_identifier(profile.ais_id)] = profile
        profiles_by_id[_normalize_user_identifier(profile.face_id)] = profile

    latest_name_by_id = {}
    for log in logs:
        user_id = log['user_id']
        if user_id and user_id not in latest_name_by_id:
            latest_name_by_id[user_id] = log['full_name']

    missing_ids = [user_id for user_id in resolved_ids if user_id not in profiles_by_id]
    for missing_id in missing_ids:
        first_name, last_name = _split_full_name(latest_name_by_id.get(missing_id, ''))
        profile = UserProfile.objects.filter(
            Q(ais_id=missing_id) | Q(face_id=missing_id)
        ).first()
        if profile is None:
            try:
                profile = UserProfile.objects.create(
                    ais_id=missing_id,
                    face_id=missing_id,
                    first_name=first_name,
                    last_name=last_name,
                    role=UserProfile.Role.STUDENT,
                    is_active=True,
                )
            except IntegrityError:
                profile = UserProfile.objects.filter(
                    Q(ais_id=missing_id) | Q(face_id=missing_id)
                ).first()
                if profile is None:
                    continue
        profiles_by_id[_normalize_user_identifier(profile.ais_id)] = profile
        profiles_by_id[_normalize_user_identifier(profile.face_id)] = profile

    users_by_id = {}
    for log in logs:
        user_id = log['user_id']
        if not user_id:
            continue
        profile = profiles_by_id.get(user_id)
        role = profile.role if profile else UserProfile.Role.STUDENT
        role_display = profile.get_role_display() if profile else 'Talaba'
        if user_id not in users_by_id:
            users_by_id[user_id] = {
                'user_id': user_id,
                'full_name': profile.get_full_name() if profile else log['full_name'],
                'role': role,
                'role_display': role_display,
                'last_seen': log['timestamp'],
                'pass_count': 1,
            }
        else:
            users_by_id[user_id]['pass_count'] += 1
            if log['timestamp'] > users_by_id[user_id]['last_seen']:
                users_by_id[user_id]['last_seen'] = log['timestamp']

    users = list(users_by_id.values())

    if role_filter in UserProfile.Role.values:
        users = [user for user in users if user['role'] == role_filter]
    else:
        role_filter = 'all'

    if search_query:
        q = search_query.lower()
        users = [
            user for user in users
            if q in user['user_id'].lower() or q in user['full_name'].lower()
        ]

    users.sort(key=lambda x: x['last_seen'], reverse=True)
    return users, role_filter


def _get_turnstile_logs_cached(target_devices, day_start, day_end, tashkent_tz):
    device_part = '-'.join(str(device.id) for device in target_devices) if target_devices else 'none'
    cache_key = (
        f"monitoring_turnstile_logs:"
        f"{day_start.strftime('%Y%m%d%H%M%S')}:"
        f"{day_end.strftime('%Y%m%d%H%M%S')}:"
        f"{device_part}"
    )
    cached_logs = cache.get(cache_key)
    if cached_logs is not None:
        return cached_logs

    logs = []
    for device in target_devices:
        success, _err, device_logs = fetch_real_attendance_logs(
            device,
            start_time=day_start,
            end_time=day_end,
        )
        if not success:
            continue
        for log in device_logs:
            ts = log.get('timestamp')
            if ts is None:
                continue
            if timezone.is_naive(ts):
                ts = timezone.make_aware(ts, tashkent_tz)
            if not (day_start <= ts <= day_end):
                continue

            full_name = (log.get('name') or '').strip() or "Noma'lum"
            user_id = _normalize_user_identifier(log.get('employee_id'))
            direction = (log.get('direction') or 'in').lower()
            if direction not in ('in', 'out'):
                direction = 'in'

            logs.append({
                'timestamp': ts,
                'full_name': full_name,
                'user_id': user_id,
                'direction': direction,
                'device_name': log.get('device_name') or device.name,
                'device_id': device.id,
            })

    cache.set(cache_key, logs, timeout=30)
    return logs
