from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.cache import cache
from django.db import IntegrityError
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.devices.models import Device, DeviceLog
from apps.groups.models import Group
from apps.groups.models import GroupStudent
from apps.rooms.models import Room
from apps.subjects.models import Subject
from apps.user_management.models import UserProfile
from apps.devices.services.hikvision_real import fetch_real_attendance_logs

from .models import GroupSubject, LessonSlot
import logging

logger = logging.getLogger(__name__)


def _posted_is_active(request):
    return request.POST.get('is_active') == 'active'


def _validation_messages(exc):
    if hasattr(exc, 'error_dict'):
        flat = []
        for errs in exc.error_dict.values():
            flat.extend(errs)
        return flat[0] if flat else str(exc)
    return exc.messages[0] if exc.messages else str(exc)


@login_required
def group_subject_list(request):
    error = None
    if request.method == 'POST':
        gid = request.POST.get('group')
        sid = request.POST.get('subject')
        tid = request.POST.get('teacher')
        is_active = _posted_is_active(request)
        if not all([gid, sid, tid]):
            error = "Barcha maydonlarni to'ldiring."
        else:
            try:
                gs = GroupSubject(
                    group_id=int(gid),
                    subject_id=int(sid),
                    teacher_id=int(tid),
                    is_active=is_active,
                )
                gs.save()
                return redirect(request.path)
            except (ValueError, TypeError):
                error = "Noto'g'ri ma'lumot."
            except ValidationError as e:
                error = _validation_messages(e)
            except IntegrityError:
                error = 'Bu guruhda bu fan allaqachon biriktirilgan.'

    qs = GroupSubject.objects.select_related('group', 'subject', 'teacher').order_by(
        'group__group_name', 'subject__subject_name'
    )
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'schedule/group_subject_list.html',
        {
            'group_subjects': page_obj,
            'page_obj': page_obj,
            'paginator': paginator,
            'total_count': paginator.count,
            'groups': Group.objects.filter(is_active=True).order_by('group_name'),
            'subjects': Subject.objects.filter(is_active=True).order_by('subject_name'),
            'teachers': UserProfile.objects.filter(
                is_active=True, role=UserProfile.Role.TEACHER
            ).order_by('last_name', 'first_name'),
            'error': error,
        },
    )


@login_required
@require_POST
def update_group_subject(request, pk):
    gs = get_object_or_404(
        GroupSubject.objects.select_related('group', 'subject', 'teacher'), pk=pk
    )
    gid = request.POST.get('group')
    sid = request.POST.get('subject')
    tid = request.POST.get('teacher')
    is_active = _posted_is_active(request)
    if not all([gid, sid, tid]):
        return JsonResponse(
            {'success': False, 'error': "Barcha maydonlarni to'ldiring."},
            status=400,
        )
    try:
        gs.group_id = int(gid)
        gs.subject_id = int(sid)
        gs.teacher_id = int(tid)
        gs.is_active = is_active
        gs.save()
    except (ValueError, TypeError):
        return JsonResponse(
            {'success': False, 'error': "Noto'g'ri ma'lumot."},
            status=400,
        )
    except ValidationError as e:
        return JsonResponse(
            {'success': False, 'error': _validation_messages(e)},
            status=400,
        )
    except IntegrityError:
        return JsonResponse(
            {'success': False, 'error': 'Bu guruhda bu fan allaqachon mavjud.'},
            status=400,
        )

    return JsonResponse({
        'success': True,
        'item': {
            'id': gs.id,
            'group_id': gs.group_id,
            'group_name': gs.group.group_name,
            'subject_id': gs.subject_id,
            'subject_name': gs.subject.subject_name,
            'teacher_id': gs.teacher_id,
            'teacher_name': gs.teacher.get_full_name(),
            'is_active': gs.is_active,
        },
    })


@login_required
@require_POST
def toggle_group_subject(request, pk):
    gs = get_object_or_404(GroupSubject, pk=pk)
    gs.is_active = not gs.is_active
    gs.save()
    return JsonResponse({'success': True, 'is_active': gs.is_active})


@login_required
@require_POST
def delete_group_subject(request, pk):
    gs = get_object_or_404(GroupSubject, pk=pk)
    gs.delete()
    return JsonResponse({'success': True})


@login_required
def lesson_slot_list(request):
    error = None
    if request.method == 'POST':
        gsid = request.POST.get('group_subject')
        rid = request.POST.get('room')
        weekday = request.POST.get('weekday')
        lesson_number = request.POST.get('lesson_number')
        is_active = _posted_is_active(request)
        if not all([gsid, rid, weekday, lesson_number]):
            error = "Barcha maydonlarni to'g'ri to'ldiring."
        else:
            try:
                ls = LessonSlot(
                    group_subject_id=int(gsid),
                    room_id=int(rid),
                    weekday=int(weekday),
                    lesson_number=int(lesson_number),
                    is_active=is_active,
                )
                ls.save()
                return redirect(request.path)
            except (ValueError, TypeError):
                error = "Noto'g'ri ma'lumot."
            except ValidationError as e:
                error = _validation_messages(e)

    qs = LessonSlot.objects.select_related(
        'group_subject__group',
        'group_subject__subject',
        'group_subject__teacher',
        'room',
    ).order_by('weekday', 'lesson_number', 'group_subject__group__group_name')
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'schedule/lesson_slot_list.html',
        {
            'lesson_slots': page_obj,
            'page_obj': page_obj,
            'paginator': paginator,
            'total_count': paginator.count,
            'group_subjects': GroupSubject.objects.filter(is_active=True)
            .select_related('group', 'subject', 'teacher')
            .order_by('group__group_name', 'subject__subject_name'),
            'rooms': Room.objects.filter(is_active=True).order_by('room_name'),
            'weekdays': LessonSlot.Weekday.choices,
            'lesson_numbers': LessonSlot.LessonNumber.choices,
            'error': error,
        },
    )


@login_required
@require_POST
def update_lesson_slot(request, pk):
    ls = get_object_or_404(
        LessonSlot.objects.select_related(
            'group_subject__group', 'group_subject__subject', 'group_subject__teacher', 'room'
        ),
        pk=pk,
    )
    gsid = request.POST.get('group_subject')
    rid = request.POST.get('room')
    weekday = request.POST.get('weekday')
    lesson_number = request.POST.get('lesson_number')
    is_active = _posted_is_active(request)
    if not all([gsid, rid, weekday, lesson_number]):
        return JsonResponse(
            {'success': False, 'error': "Barcha maydonlarni to'ldiring."},
            status=400,
        )
    try:
        ls.group_subject_id = int(gsid)
        ls.room_id = int(rid)
        ls.weekday = int(weekday)
        ls.lesson_number = int(lesson_number)
        ls.is_active = is_active
        ls.save()
    except (ValueError, TypeError):
        return JsonResponse(
            {'success': False, 'error': "Noto'g'ri ma'lumot."},
            status=400,
        )
    except ValidationError as e:
        return JsonResponse(
            {'success': False, 'error': _validation_messages(e)},
            status=400,
        )

    return JsonResponse({
        'success': True,
        'item': {
            'id': ls.id,
            'group_subject_id': ls.group_subject_id,
            'group_subject_label': str(ls.group_subject),
            'teacher_name': ls.group_subject.teacher.get_full_name(),
            'room_id': ls.room_id,
            'room_name': ls.room.room_name,
            'weekday': ls.weekday,
            'weekday_display': ls.get_weekday_display(),
            'lesson_number': ls.lesson_number,
            'lesson_number_display': ls.get_lesson_number_display(),
            'start_time': ls.start_time.strftime('%H:%M'),
            'end_time': ls.end_time.strftime('%H:%M'),
            'is_active': ls.is_active,
        },
    })


@login_required
@require_POST
def toggle_lesson_slot(request, pk):
    ls = get_object_or_404(LessonSlot, pk=pk)
    ls.is_active = not ls.is_active
    ls.save()
    return JsonResponse({'success': True, 'is_active': ls.is_active})


@login_required
@require_POST
def delete_lesson_slot(request, pk):
    ls = get_object_or_404(LessonSlot, pk=pk)
    ls.delete()
    return JsonResponse({'success': True})


def _get_linked_teacher_profile(user):
    if not user.is_authenticated:
        return None
    return UserProfile.objects.filter(
        auth_user=user,
        role=UserProfile.Role.TEACHER,
        is_active=True,
    ).first()


def _parse_selected_date(request, tashkent_tz):
    selected_date_str = (request.GET.get('date') or '').strip()
    if selected_date_str:
        try:
            return datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    # Hozirgi vaqtni Toshkent vaqt zonasida olamiz
    current_date = timezone.localtime(timezone.now(), tashkent_tz).date()
    return current_date


def _room_device_or_none(room):
    try:
        return room.attendance_device
    except Device.DoesNotExist:
        return None


@login_required
def teacher_dashboard(request):
    teacher_profile = _get_linked_teacher_profile(request.user)
    if teacher_profile is None:
        return HttpResponseForbidden("Bu sahifa faqat teacher uchun.")

    weekly_slots = list(
        LessonSlot.objects.filter(
            group_subject__teacher=teacher_profile,
            group_subject__is_active=True,
            is_active=True,
        ).select_related('group_subject__group')
    )
    weekly_minutes = sum(
        ((slot.end_time.hour * 60 + slot.end_time.minute) - (slot.start_time.hour * 60 + slot.start_time.minute))
        for slot in weekly_slots
    )
    weekly_hours = round(weekly_minutes / 60, 1)

    assignments = GroupSubject.objects.filter(
        teacher=teacher_profile,
        is_active=True,
    ).select_related('group', 'subject')
    groups = sorted({assignment.group.group_name for assignment in assignments})

    return render(request, 'schedule/teacher_dashboard.html', {
        'teacher_profile': teacher_profile,
        'weekly_hours': weekly_hours,
        'groups': groups,
        'assignments': assignments,
    })


@login_required
def teacher_attendance(request):
    teacher_profile = _get_linked_teacher_profile(request.user)
    if teacher_profile is None:
        return HttpResponseForbidden("Bu sahifa faqat teacher uchun.")

    tashkent_tz = timezone.get_fixed_timezone(300)  # UTC+5 for Tashkent
    selected_date = _parse_selected_date(request, tashkent_tz)
    selected_weekday = selected_date.isoweekday()
    day_buttons = [
        selected_date + timedelta(days=offset)
        for offset in range(-3, 4)
    ]

    assignments = GroupSubject.objects.filter(
        teacher=teacher_profile,
        is_active=True,
    )
    slots = LessonSlot.objects.filter(
        group_subject__in=assignments,
        is_active=True,
        weekday=selected_weekday,
    ).select_related('group_subject__group', 'group_subject__subject', 'room').order_by('lesson_number')

    slot_rows = []
    for slot in slots:
        room_device = _room_device_or_none(slot.room)
        has_room_device = bool(
            room_device and room_device.is_active and room_device.device_type == 'room'
        )
        slot_rows.append({
            'slot': slot,
            'has_room_device': has_room_device,
            'room_device_name': room_device.name if room_device else '',
        })

    return render(request, 'schedule/teacher_attendance_list.html', {
        'teacher_profile': teacher_profile,
        'day_buttons': day_buttons,
        'slot_rows': slot_rows,
        'selected_date': selected_date.strftime('%Y-%m-%d'),
    })


@login_required
def teacher_attendance_detail(request, lesson_slot_pk):
    teacher_profile = _get_linked_teacher_profile(request.user)
    if teacher_profile is None:
        return HttpResponseForbidden("Bu sahifa faqat teacher uchun.")

    lesson_slot = get_object_or_404(
        LessonSlot.objects.select_related(
            'group_subject__group',
            'group_subject__subject',
            'group_subject__teacher',
            'room',
        ),
        pk=lesson_slot_pk,
        is_active=True,
        group_subject__teacher=teacher_profile,
        group_subject__is_active=True,
    )
    group_subject = lesson_slot.group_subject

    tashkent_tz = timezone.get_fixed_timezone(300)  # UTC+5 for Tashkent
    selected_date = _parse_selected_date(request, tashkent_tz)
    day_start = timezone.make_aware(
        datetime.combine(selected_date, datetime.min.time()),
        tashkent_tz,
    )
    day_end = timezone.make_aware(
        datetime.combine(selected_date, datetime.max.time()),
        tashkent_tz,
    )

    memberships = list(
        GroupStudent.objects.filter(
            group=group_subject.group,
            is_active=True,
            student__is_active=True,
        )
        .select_related('student')
        .order_by('student__last_name', 'student__first_name')
    )
    students = [membership.student for membership in memberships]
    student_ids = [student.id for student in students]

    university_present_ids = set(
        DeviceLog.objects.filter(
            user_id__in=student_ids,
            device__device_type='entry',
            timestamp__range=(day_start, day_end),
        ).values_list('user_id', flat=True).distinct()
    )

    room_device = _room_device_or_none(lesson_slot.room)
    has_room_device = bool(
        room_device and room_device.is_active and room_device.device_type == 'room'
    )
    
    lesson_present_ids = set()
    lesson_entry_times = {}
    if has_room_device:
        slot_start = timezone.make_aware(
            datetime.combine(selected_date, lesson_slot.start_time),
            tashkent_tz,
        )
        slot_end = timezone.make_aware(
            datetime.combine(selected_date, lesson_slot.end_time),
            tashkent_tz,
        )
        
        lesson_logs = DeviceLog.objects.filter(
            user_id__in=student_ids,
            device_id=room_device.id,
            timestamp__range=(slot_start, slot_end),
        ).order_by('timestamp')
        
        for log in lesson_logs:
            if log.user_id not in lesson_entry_times:
                lesson_entry_times[log.user_id] = log.timestamp
        
        lesson_present_ids = set(lesson_entry_times.keys())
    else:
        # Agar xona device bo'lmasa, barcha turniketlardan o'tganlarni tekshiramiz
        slot_start = timezone.make_aware(
            datetime.combine(selected_date, lesson_slot.start_time),
            tashkent_tz,
        )
        slot_end = timezone.make_aware(
            datetime.combine(selected_date, lesson_slot.end_time),
            tashkent_tz,
        )
        
        # Barcha entry device lardan o'tganlarni qidiramiz
        all_logs = DeviceLog.objects.filter(
            user_id__in=student_ids,
            device__device_type='entry',
            timestamp__range=(slot_start, slot_end),
        ).order_by('timestamp')
        
        for log in all_logs:
            if log.user_id not in lesson_entry_times:
                lesson_entry_times[log.user_id] = log.timestamp
        
        lesson_present_ids = set(lesson_entry_times.keys())
        has_room_device = True  # Override to show results

    student_rows = []
    for student in students:
        if not has_room_device:
            lesson_status = "Xonaga device biriktirilmagan"
            lesson_present = None
            entry_time = None
            is_late = False
        else:
            lesson_present = student.id in lesson_present_ids
            entry_time = lesson_entry_times.get(student.id)
            
            # Kechikib kelganligini tekshirish
            is_late = False
            if lesson_present and entry_time:
                # Ensure entry_time is timezone-aware and comparable to slot_start
                if timezone.is_naive(entry_time):
                    entry_time = timezone.make_aware(entry_time, tashkent_tz)

                slot_start = timezone.make_aware(
                    datetime.combine(selected_date, lesson_slot.start_time),
                    tashkent_tz,
                )

                logger.debug(
                    "%s - entry: %s, start: %s, late_threshold: %s",
                    student,
                    entry_time,
                    slot_start,
                    slot_start + timedelta(minutes=20),
                )
                # Dars boshlangandan 20 minutdan ko'p kechiksa
                if entry_time > slot_start + timedelta(minutes=20):
                    is_late = True
                    lesson_status = 'Kechikib keldi'
                    logger.debug("%s kechikib keldi!", student)
                else:
                    lesson_status = 'Keldi'
            elif lesson_present:
                lesson_status = 'Keldi'
            else:
                lesson_status = 'Kelmagan'

        student_rows.append({
            'student': student,
            'university_present': student.id in university_present_ids,
            'lesson_present': lesson_present,
            'lesson_status': lesson_status,
            'entry_time': entry_time,
            'is_late': is_late,
        })

    # Statistikani hisoblash
    total_students = len(student_rows)
    present_count = sum(1 for row in student_rows if row['lesson_present'])
    absent_count = total_students - present_count
    late_count = sum(1 for row in student_rows if row.get('is_late'))

    return render(request, 'schedule/teacher_attendance_detail.html', {
        'teacher_profile': teacher_profile,
        'group_subject': group_subject,
        'lesson_slot': lesson_slot,
        'student_rows': student_rows,
        'selected_date': selected_date.strftime('%Y-%m-%d'),
        'has_room_device': has_room_device,
        'room_device_name': room_device.name if room_device else '',
        'total_students': total_students,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
    })


@login_required
def teacher_schedule(request):
    teacher_profile = _get_linked_teacher_profile(request.user)
    if teacher_profile is None:
        return HttpResponseForbidden("Bu sahifa faqat teacher uchun.")

    weekly_slots = LessonSlot.objects.filter(
        group_subject__teacher=teacher_profile,
        group_subject__is_active=True,
        is_active=True,
    ).select_related('group_subject__group', 'group_subject__subject', 'room').order_by(
        'weekday', 'lesson_number'
    )

    slots_by_weekday = {weekday: [] for weekday, _label in LessonSlot.Weekday.choices}
    for slot in weekly_slots:
        slots_by_weekday[slot.weekday].append(slot)

    weekday_labels = dict(LessonSlot.Weekday.choices)
    weekdays = [
        {
            'value': weekday,
            'label': weekday_labels[weekday],
            'slots': slots_by_weekday[weekday],
        }
        for weekday, _label in LessonSlot.Weekday.choices
    ]

    return render(request, 'schedule/teacher_schedule.html', {
        'teacher_profile': teacher_profile,
        'weekdays': weekdays,
    })


@login_required
def teacher_monitoring(request):
    """
    Teacher uchun monitoring sahifasi.
    Faqat o'zining guruhlari va o'qitadigan kunlaridagi
    turniket loglarini ko'rsatadi.
    """
    teacher_profile = _get_linked_teacher_profile(request.user)
    if teacher_profile is None:
        return HttpResponseForbidden("Bu sahifa faqat teacher uchun.")

    tashkent_tz = timezone.get_fixed_timezone(300)  # UTC+5 for Tashkent
    today = timezone.localtime(timezone.now(), tashkent_tz).date()
    last_10_dates = [today - timedelta(days=i) for i in range(10)]
    last_10_days = [d.strftime('%Y-%m-%d') for d in last_10_dates]

    # Tanlangan sana
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
        datetime.combine(selected_date, datetime.min.time()), tashkent_tz
    )
    day_end = timezone.make_aware(
        datetime.combine(selected_date, datetime.max.time()), tashkent_tz
    )

    # O'sha kunda o'qituvchining darslari bor guruhlarini topish
    selected_weekday = selected_date.isoweekday()
    teacher_groups = Group.objects.filter(
        group_subjects__teacher=teacher_profile,
        group_subjects__is_active=True,
        group_subjects__lesson_slots__weekday=selected_weekday,
        group_subjects__lesson_slots__is_active=True,
    ).distinct()

    # Guruh talabalari
    from apps.groups.models import GroupStudent
    student_profiles = list(
        GroupStudent.objects.filter(
            group__in=teacher_groups,
            is_active=True,
            student__is_active=True,
        ).select_related('student').values_list('student', flat=True)
    )

    # Turniket loglarini olish (faqat kirish qurilmalaridan)
    entry_devices = list(Device.objects.filter(is_active=True, device_type='entry').order_by('name'))

    logs = _get_teacher_monitoring_logs(
        devices=entry_devices,
        day_start=day_start,
        day_end=day_end,
        tashkent_tz=tashkent_tz,
    )

    # Qidirish
    search_query = request.GET.get('q', '').strip()

    # Foydalanuvchilarni logs dan yig'ish
    from django.db.models import Q as DQ
    from apps.user_management.models import UserProfile as UP

    resolved_ids = {log['user_id'] for log in logs if log['user_id']}
    profiles_by_id = {}
    if resolved_ids:
        for p in UP.objects.filter(DQ(ais_id__in=resolved_ids) | DQ(face_id__in=resolved_ids)):
            nid = _normalize_uid(p.ais_id)
            profiles_by_id[nid] = p
            profiles_by_id[_normalize_uid(p.face_id)] = p

    users_by_id = {}
    for log in logs:
        uid = log['user_id']
        if not uid:
            continue
        profile = profiles_by_id.get(uid)
        is_my_student = (profile.id in student_profiles) if profile else False
        if uid not in users_by_id:
            users_by_id[uid] = {
                'user_id': uid,
                'full_name': profile.get_full_name() if profile else log['full_name'],
                'role': profile.role if profile else 'student',
                'role_display': profile.get_role_display() if profile else 'Talaba',
                'is_my_student': is_my_student,
                'last_seen': log['timestamp'],
                'pass_count': 1,
            }
        else:
            users_by_id[uid]['pass_count'] += 1
            if log['timestamp'] > users_by_id[uid]['last_seen']:
                users_by_id[uid]['last_seen'] = log['timestamp']

    users = list(users_by_id.values())

    # Filter: faqat o'z talabalari yoki hammasi
    show_filter = request.GET.get('show', 'my').strip()  # 'my' | 'all'
    if show_filter == 'my':
        users = [u for u in users if u['is_my_student']]

    if search_query:
        q = search_query.lower()
        users = [u for u in users if q in u['full_name'].lower() or q in u['user_id'].lower()]

    users.sort(key=lambda x: x['last_seen'], reverse=True)

    from django.core.paginator import Paginator
    paginator = Paginator(users, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'schedule/teacher_monitoring.html', {
        'teacher_profile': teacher_profile,
        'users': page_obj.object_list,
        'page_obj': page_obj,
        'total_count': paginator.count,
        'selected_date': selected_date.strftime('%Y-%m-%d'),
        'last_10_days': last_10_days,
        'q': search_query,
        'show_filter': show_filter,
        'teacher_groups': teacher_groups,
    })

def _normalize_uid(value):
    identifier = str(value or '').strip()
    if identifier.isdigit():
        return identifier.lstrip('0') or '0'
    return identifier

def _get_teacher_monitoring_logs(devices, day_start, day_end, tashkent_tz):
    from django.core.cache import cache
    from apps.devices.services.hikvision_real import fetch_real_attendance_logs

    device_part = '-'.join(str(d.id) for d in devices) if devices else 'none'
    cache_key = (
        f"teacher_monitoring_logs:"
        f"{day_start.strftime('%Y%m%d')}:"
        f"{device_part}"
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    logs = []
    for device in devices:
        success, _err, device_logs = fetch_real_attendance_logs(
            device, start_time=day_start, end_time=day_end
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
            uid = _normalize_uid(log.get('employee_id'))
            logs.append({
                'timestamp': ts,
                'full_name': full_name,
                'user_id': uid,
                'device_name': log.get('device_name') or device.name,
            })

    cache.set(cache_key, logs, timeout=60)
    return logs
