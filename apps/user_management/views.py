from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from attendance_system.spreadsheet import build_xlsx, parse_active_value, read_xlsx

from .models import UserProfile


STUDENT_IMPORT_HEADERS = ['Face ID', 'AIS ID', 'Familya', 'Ism', 'Holati']
STUDENT_IMPORT_SAMPLE = [['FACE-1001', 'AIS-1001', 'Karimov', 'Ali', 'Faol']]
AuthUser = get_user_model()


def _posted_is_active(request):
    return request.POST.get('is_active') == 'active'


def _excel_response(filename, headers, example_rows, sheet_name):
    response = HttpResponse(
        build_xlsx(headers, example_rows, sheet_name=sheet_name),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _student_redirect():
    return redirect('user_management:student_list')


@login_required
def user_list(request, role_scope=None):
    if role_scope is not None and role_scope not in UserProfile.Role.values:
        role_scope = None

    titles = {
        UserProfile.Role.STUDENT: "Talabalar boshqaruvi",
        UserProfile.Role.TEACHER: "O'qituvchilar boshqaruvi",
        UserProfile.Role.STAFF: 'Xodimlar boshqaruvi',
    }
    list_page_title = titles.get(role_scope, 'Foydalanuvchilar boshqaruvi')
    role_labels = dict(UserProfile.Role.choices)
    role_scope_label = role_labels.get(role_scope, '') if role_scope else ''
    nav_section = {
        UserProfile.Role.STUDENT: 'students',
        UserProfile.Role.TEACHER: 'teachers',
        UserProfile.Role.STAFF: 'staff',
    }.get(role_scope, 'users')

    error = None

    if request.method == 'POST':
        face_id = request.POST.get('face_id', '').strip()
        ais_id = request.POST.get('ais_id', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        role = role_scope if role_scope else request.POST.get('role', 'student')
        is_active = _posted_is_active(request)

        if not all([face_id, ais_id, last_name, first_name]):
            error = "Barcha maydonlarni to'ldiring."
        elif role not in UserProfile.Role.values:
            error = "Lavozim noto'g'ri tanlangan."
        else:
            try:
                UserProfile.objects.create(
                    face_id=face_id,
                    ais_id=ais_id,
                    last_name=last_name,
                    first_name=first_name,
                    role=role,
                    is_active=is_active,
                )
                return redirect(request.path)
            except IntegrityError:
                error = "Bu Face ID yoki AIS ID allaqachon mavjud!"

    users_queryset = UserProfile.objects.select_related('auth_user').all()
    if role_scope:
        users_queryset = users_queryset.filter(role=role_scope)
    paginator = Paginator(users_queryset.order_by('last_name', 'first_name'), 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'user_management/user_list.html', {
        'users': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'total_users': paginator.count,
        'error': error,
        'role_choices': UserProfile.Role.choices,
        'role_scope': role_scope,
        'list_page_title': list_page_title,
        'nav_section': nav_section,
        'role_scope_label': role_scope_label,
    })


@login_required
def download_student_template(request):
    return _excel_response(
        'talabalar_import_shablon.xlsx',
        STUDENT_IMPORT_HEADERS,
        STUDENT_IMPORT_SAMPLE,
        'Talabalar',
    )


@login_required
@require_POST
def import_students(request):
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        messages.error(request, 'Import uchun Excel fayl tanlang.')
        return _student_redirect()

    try:
        rows = read_xlsx(uploaded_file)
        created_count = 0
        updated_count = 0
        with transaction.atomic():
            for row_number, row in enumerate(rows, start=2):
                face_id = row.get('Face ID', '').strip()
                ais_id = row.get('AIS ID', '').strip()
                last_name = row.get('Familya', '').strip()
                first_name = row.get('Ism', '').strip()
                is_active = parse_active_value(row.get('Holati', ''), default=True)

                if not all([face_id, ais_id, last_name, first_name]):
                    raise ValueError(f'{row_number}-qatorda barcha ustunlar to`ldirilishi kerak.')

                existing_face = UserProfile.objects.filter(face_id=face_id).first()
                existing_ais = UserProfile.objects.filter(ais_id=ais_id).first()

                if existing_face and existing_ais and existing_face.pk != existing_ais.pk:
                    raise ValueError(f'{row_number}-qatorda Face ID va AIS ID turli foydalanuvchilarga tegishli.')

                profile = existing_face or existing_ais
                if profile and profile.role != UserProfile.Role.STUDENT:
                    raise ValueError(f'{row_number}-qatordagi foydalanuvchi talaba emas.')

                if profile:
                    profile.face_id = face_id
                    profile.ais_id = ais_id
                    profile.last_name = last_name
                    profile.first_name = first_name
                    profile.role = UserProfile.Role.STUDENT
                    profile.is_active = is_active
                    profile.save(update_fields=['face_id', 'ais_id', 'last_name', 'first_name', 'role', 'is_active'])
                    updated_count += 1
                else:
                    UserProfile.objects.create(
                        face_id=face_id,
                        ais_id=ais_id,
                        last_name=last_name,
                        first_name=first_name,
                        role=UserProfile.Role.STUDENT,
                        is_active=is_active,
                    )
                    created_count += 1
    except Exception as exc:
        messages.error(request, f'Import xatoligi: {exc}')
        return _student_redirect()

    messages.success(
        request,
        f'Talabalar import qilindi: {created_count} ta yangi, {updated_count} ta yangilandi.',
    )
    return _student_redirect()


@login_required
@require_POST
def delete_user(request, user_id):
    try:
        user = UserProfile.objects.get(id=user_id)
        if user.auth_user_id:
            user.auth_user.delete()
        user.delete()
        return JsonResponse({'success': True})
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False}, status=404)


@login_required
@require_POST
def update_user(request, user_id):
    user = get_object_or_404(UserProfile.objects.select_related('auth_user'), id=user_id)

    face_id = request.POST.get('face_id', '').strip()
    ais_id = request.POST.get('ais_id', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    first_name = request.POST.get('first_name', '').strip()
    role = request.POST.get('role', 'student')
    is_active = _posted_is_active(request)
    login_username = request.POST.get('login_username', '').strip()
    login_password = request.POST.get('login_password', '')

    if not all([face_id, ais_id, last_name, first_name]):
        return JsonResponse({'success': False, 'error': "Barcha maydonlarni to'ldiring."}, status=400)

    if role not in UserProfile.Role.values:
        return JsonResponse({'success': False, 'error': "Lavozim noto'g'ri tanlangan."}, status=400)

    duplicate = UserProfile.objects.exclude(id=user.id).filter(face_id=face_id).exists()
    duplicate = duplicate or UserProfile.objects.exclude(id=user.id).filter(ais_id=ais_id).exists()
    if duplicate:
        return JsonResponse({'success': False, 'error': "Bu Face ID yoki AIS ID allaqachon mavjud!"}, status=400)

    if role == UserProfile.Role.TEACHER and (login_username or login_password):
        target_username = login_username or (user.auth_user.username if user.auth_user_id else '')
        if not target_username:
            return JsonResponse({'success': False, 'error': "Teacher uchun login kiriting."}, status=400)
        if not login_password:
            return JsonResponse({'success': False, 'error': "Teacher uchun parol kiriting."}, status=400)

        duplicate_username_qs = AuthUser.objects.filter(username=target_username)
        if user.auth_user_id:
            duplicate_username_qs = duplicate_username_qs.exclude(id=user.auth_user_id)
        if duplicate_username_qs.exists():
            return JsonResponse({'success': False, 'error': "Bu login allaqachon band."}, status=400)

        auth_user = user.auth_user if user.auth_user_id else AuthUser()
        auth_user.username = target_username
        auth_user.set_password(login_password)
        auth_user.save()
        user.auth_user = auth_user

    user.face_id = face_id
    user.ais_id = ais_id
    user.last_name = last_name
    user.first_name = first_name
    user.role = role
    user.is_active = is_active
    update_fields = ['face_id', 'ais_id', 'last_name', 'first_name', 'role', 'is_active']
    if role == UserProfile.Role.TEACHER and (login_username or login_password):
        update_fields.append('auth_user')
    user.save(update_fields=update_fields)

    return JsonResponse({
        'success': True,
        'user': {
            'id': user.id,
            'face_id': user.face_id,
            'ais_id': user.ais_id,
            'last_name': user.last_name,
            'first_name': user.first_name,
            'full_name': user.get_full_name(),
            'initials': f"{user.last_name[:1]}{user.first_name[:1]}".upper(),
            'role': user.role,
            'role_display': user.get_role_display(),
            'is_active': user.is_active,
            'login_username': user.auth_user.username if user.auth_user_id else '',
        }
    })


@login_required
@require_POST
def toggle_user_status(request, user_id):
    user = get_object_or_404(UserProfile, id=user_id)
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    return JsonResponse({'success': True, 'is_active': user.is_active})
