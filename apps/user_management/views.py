from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import IntegrityError
from django.core.paginator import Paginator
from .models import UserProfile


def _posted_is_active(request):
    return request.POST.get('is_active') == 'active'


@login_required
def user_list(request):
    error = None

    if request.method == 'POST':
        face_id    = request.POST.get('face_id', '').strip()
        ais_id     = request.POST.get('ais_id', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        role       = request.POST.get('role', 'student')
        is_active  = _posted_is_active(request)

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
                return redirect('user_management:user_list')
            except IntegrityError:
                error = "Bu Face ID yoki AIS ID allaqachon mavjud!"

    users_queryset = UserProfile.objects.all()
    paginator = Paginator(users_queryset, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'user_management/user_list.html', {
        'users': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'total_users': paginator.count,
        'error': error,
        'role_choices': UserProfile.Role.choices,
    })


@login_required
@require_POST
def delete_user(request, user_id):
    try:
        user = UserProfile.objects.get(id=user_id)
        user.delete()
        return JsonResponse({'success': True})
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False}, status=404)


@login_required
@require_POST
def update_user(request, user_id):
    user = get_object_or_404(UserProfile, id=user_id)

    face_id    = request.POST.get('face_id', '').strip()
    ais_id     = request.POST.get('ais_id', '').strip()
    last_name  = request.POST.get('last_name', '').strip()
    first_name = request.POST.get('first_name', '').strip()
    role       = request.POST.get('role', 'student')
    is_active  = _posted_is_active(request)

    if not all([face_id, ais_id, last_name, first_name]):
        return JsonResponse({'success': False, 'error': "Barcha maydonlarni to'ldiring."}, status=400)

    if role not in UserProfile.Role.values:
        return JsonResponse({'success': False, 'error': "Lavozim noto'g'ri tanlangan."}, status=400)

    duplicate = UserProfile.objects.exclude(id=user.id).filter(face_id=face_id).exists()
    duplicate = duplicate or UserProfile.objects.exclude(id=user.id).filter(ais_id=ais_id).exists()
    if duplicate:
        return JsonResponse({'success': False, 'error': "Bu Face ID yoki AIS ID allaqachon mavjud!"}, status=400)

    user.face_id = face_id
    user.ais_id = ais_id
    user.last_name = last_name
    user.first_name = first_name
    user.role = role
    user.is_active = is_active
    user.save(update_fields=['face_id', 'ais_id', 'last_name', 'first_name', 'role', 'is_active'])

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
        }
    })


@login_required
@require_POST
def toggle_user_status(request, user_id):
    user = get_object_or_404(UserProfile, id=user_id)
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    return JsonResponse({'success': True, 'is_active': user.is_active})
