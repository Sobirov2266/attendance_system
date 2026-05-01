from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Group


def _posted_is_active(request):
    return request.POST.get('is_active') == 'active'


@login_required
def group_list(request):
    error = None

    if request.method == 'POST':
        group_id = request.POST.get('group_id', '').strip()
        group_name = request.POST.get('group_name', '').strip()
        is_active = _posted_is_active(request)

        if not all([group_id, group_name]):
            error = "Barcha maydonlarni to'ldiring."
        else:
            try:
                Group.objects.create(
                    group_id=group_id,
                    group_name=group_name,
                    is_active=is_active,
                )
                return redirect('groups:group_list')
            except IntegrityError:
                error = "Bu Group ID yoki guruh nomi allaqachon mavjud!"

    groups_queryset = Group.objects.all()
    paginator = Paginator(groups_queryset, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'groups/group_list.html', {
        'groups': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'total_groups': paginator.count,
        'error': error,
    })


@login_required
@require_POST
def update_group(request, group_pk):
    group = get_object_or_404(Group, pk=group_pk)
    group_id = request.POST.get('group_id', '').strip()
    group_name = request.POST.get('group_name', '').strip()
    is_active = _posted_is_active(request)

    if not all([group_id, group_name]):
        return JsonResponse({'success': False, 'error': "Barcha maydonlarni to'ldiring."}, status=400)

    duplicate = Group.objects.exclude(pk=group.pk).filter(group_id=group_id).exists()
    duplicate = duplicate or Group.objects.exclude(pk=group.pk).filter(group_name=group_name).exists()
    if duplicate:
        return JsonResponse({'success': False, 'error': "Bu Group ID yoki guruh nomi allaqachon mavjud!"}, status=400)

    group.group_id = group_id
    group.group_name = group_name
    group.is_active = is_active
    group.save(update_fields=['group_id', 'group_name', 'is_active'])

    return JsonResponse({
        'success': True,
        'group': {
            'id': group.id,
            'group_id': group.group_id,
            'group_name': group.group_name,
            'is_active': group.is_active,
        },
    })


@login_required
@require_POST
def toggle_group_status(request, group_pk):
    group = get_object_or_404(Group, pk=group_pk)
    group.is_active = not group.is_active
    group.save(update_fields=['is_active'])
    return JsonResponse({'success': True, 'is_active': group.is_active})


@login_required
@require_POST
def delete_group(request, group_pk):
    group = get_object_or_404(Group, pk=group_pk)
    group.delete()
    return JsonResponse({'success': True})
