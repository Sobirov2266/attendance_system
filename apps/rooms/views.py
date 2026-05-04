from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Room


def _posted_is_active(request):
    return request.POST.get('is_active') == 'active'


@login_required
def room_list(request):
    error = None

    if request.method == 'POST':
        room_id = request.POST.get('room_id', '').strip()
        room_name = request.POST.get('room_name', '').strip()
        is_active = _posted_is_active(request)

        if not all([room_id, room_name]):
            error = "Barcha maydonlarni to'ldiring."
        else:
            try:
                Room.objects.create(
                    room_id=room_id,
                    room_name=room_name,
                    is_active=is_active,
                )
                return redirect('rooms:room_list')
            except IntegrityError:
                error = "Bu Xona ID yoki xona nomi allaqachon mavjud!"

    rooms_queryset = Room.objects.all()
    paginator = Paginator(rooms_queryset, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'rooms/room_list.html', {
        'rooms': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'total_rooms': paginator.count,
        'error': error,
    })


@login_required
@require_POST
def update_room(request, room_pk):
    room = get_object_or_404(Room, pk=room_pk)
    room_id = request.POST.get('room_id', '').strip()
    room_name = request.POST.get('room_name', '').strip()
    is_active = _posted_is_active(request)

    if not all([room_id, room_name]):
        return JsonResponse({'success': False, 'error': "Barcha maydonlarni to'ldiring."}, status=400)

    duplicate = Room.objects.exclude(pk=room.pk).filter(room_id=room_id).exists()
    duplicate = duplicate or Room.objects.exclude(pk=room.pk).filter(room_name=room_name).exists()
    if duplicate:
        return JsonResponse({'success': False, 'error': "Bu Xona ID yoki xona nomi allaqachon mavjud!"}, status=400)

    room.room_id = room_id
    room.room_name = room_name
    room.is_active = is_active
    room.save(update_fields=['room_id', 'room_name', 'is_active'])

    return JsonResponse({
        'success': True,
        'room': {
            'id': room.id,
            'room_id': room.room_id,
            'room_name': room.room_name,
            'is_active': room.is_active,
        },
    })


@login_required
@require_POST
def toggle_room_status(request, room_pk):
    room = get_object_or_404(Room, pk=room_pk)
    room.is_active = not room.is_active
    room.save(update_fields=['is_active'])
    return JsonResponse({'success': True, 'is_active': room.is_active})


@login_required
@require_POST
def delete_room(request, room_pk):
    room = get_object_or_404(Room, pk=room_pk)
    room.delete()
    return JsonResponse({'success': True})
