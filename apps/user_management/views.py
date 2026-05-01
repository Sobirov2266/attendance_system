from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import IntegrityError
from .models import UserProfile


@login_required
def user_list(request):
    error = None

    if request.method == 'POST':
        face_id    = request.POST.get('face_id', '').strip()
        ais_id     = request.POST.get('ais_id', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        role       = request.POST.get('role', 'student')

        if not all([face_id, ais_id, last_name, first_name]):
            error = "Barcha maydonlarni to'ldiring."
        else:
            try:
                UserProfile.objects.create(
                    face_id=face_id,
                    ais_id=ais_id,
                    last_name=last_name,
                    first_name=first_name,
                    role=role,
                )
                return redirect('user_management:user_list')
            except IntegrityError:
                error = "Bu Face ID yoki AIS ID allaqachon mavjud!"

    users = UserProfile.objects.all()
    return render(request, 'user_management/user_list.html', {
        'users': users,
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