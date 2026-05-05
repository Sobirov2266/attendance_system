from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.groups.models import Group
from apps.rooms.models import Room
from apps.subjects.models import Subject
from apps.user_management.models import UserProfile

from .models import GroupSubject, LessonSlot


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
            'group_subject__group', 'group_subject__subject', 'room'
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
