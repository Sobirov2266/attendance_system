from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import redirect, render

from apps.devices.models import Device
from apps.groups.models import Group, GroupStudent
from apps.rooms.models import Room
from apps.schedule.models import GroupSubject, LessonSlot
from apps.subjects.models import Subject
from apps.user_management.models import UserProfile


@login_required
def dashboard(request):
    teacher_profile = UserProfile.objects.filter(
        auth_user=request.user,
        role=UserProfile.Role.TEACHER,
        is_active=True,
    ).first()
    if teacher_profile and not request.user.is_superuser and not request.user.is_staff:
        return redirect('schedule:teacher_attendance')

    devices = Device.objects.select_related('room').all()
    users = UserProfile.objects.all()
    groups = Group.objects.all()
    rooms = Room.objects.all()
    subjects = Subject.objects.all()
    group_subjects = GroupSubject.objects.select_related('group', 'subject', 'teacher')
    lesson_slots = LessonSlot.objects.select_related(
        'group_subject__group',
        'group_subject__subject',
        'room',
    )
    active_students = GroupStudent.objects.filter(is_active=True)
    weekday_labels = dict(LessonSlot.Weekday.choices)
    lesson_number_labels = dict(LessonSlot.LessonNumber.choices)
    weekday_load_stats = [
        {'label': weekday_labels[item['weekday']], 'total': item['total']}
        for item in lesson_slots.filter(is_active=True).values('weekday').annotate(
            total=Count('id')
        ).order_by('weekday')
    ]
    lesson_load_stats = [
        {'label': lesson_number_labels[item['lesson_number']], 'total': item['total']}
        for item in lesson_slots.filter(is_active=True).values('lesson_number').annotate(
            total=Count('id')
        ).order_by('lesson_number')
    ]

    context = {
        'device_count': devices.count(),
        'online_devices': devices.filter(is_active=True).count(),
        'offline_devices': devices.filter(is_active=False).count(),
        'entry_devices': devices.filter(device_type='entry').count(),
        'exit_devices': devices.filter(device_type='exit').count(),
        'room_devices': devices.filter(device_type='room').count(),
        'room_device_count': devices.filter(device_type='room', room__isnull=False).count(),

        'user_count': users.count(),
        'active_users': users.filter(is_active=True).count(),
        'inactive_users': users.filter(is_active=False).count(),
        'student_count': users.filter(role=UserProfile.Role.STUDENT).count(),
        'teacher_count': users.filter(role=UserProfile.Role.TEACHER).count(),
        'staff_count': users.filter(role=UserProfile.Role.STAFF).count(),

        'group_count': groups.count(),
        'active_group_count': groups.filter(is_active=True).count(),
        'inactive_group_count': groups.filter(is_active=False).count(),
        'assigned_student_count': active_students.values('student_id').distinct().count(),
        'unassigned_student_count': users.filter(role=UserProfile.Role.STUDENT).exclude(
            group_memberships__is_active=True
        ).count(),

        'room_count': rooms.count(),
        'active_room_count': rooms.filter(is_active=True).count(),
        'inactive_room_count': rooms.filter(is_active=False).count(),
        'rooms_without_device': rooms.filter(is_active=True).exclude(
            attendance_device__isnull=False
        ).count(),

        'subject_count': subjects.count(),
        'active_subject_count': subjects.filter(is_active=True).count(),
        'inactive_subject_count': subjects.filter(is_active=False).count(),

        'group_subject_count': group_subjects.count(),
        'active_group_subject_count': group_subjects.filter(is_active=True).count(),
        'lesson_slot_count': lesson_slots.count(),
        'active_lesson_slot_count': lesson_slots.filter(is_active=True).count(),
        'inactive_lesson_slot_count': lesson_slots.filter(is_active=False).count(),

        'weekday_load_stats': weekday_load_stats,
        'lesson_load_stats': lesson_load_stats,

        'recent_group_subjects': group_subjects.order_by('-created_at')[:5],
        'recent_lesson_slots': lesson_slots.order_by('weekday', 'lesson_number')[:6],
        'devices': devices.order_by('-is_active', 'name')[:6],
        'groups_summary': groups.annotate(
            students_count=Count(
                'student_memberships',
                filter=Q(student_memberships__is_active=True),
                distinct=True,
            )
        ).order_by('-students_count', 'group_name')[:5],
        'today_attendance': [],
    }
    return render(request, 'dashboard.html', context)
