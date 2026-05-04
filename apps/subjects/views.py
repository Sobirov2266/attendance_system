from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Subject


def _posted_is_active(request):
    return request.POST.get('is_active') == 'active'


@login_required
def subject_list(request):
    error = None

    if request.method == 'POST':
        subject_id = request.POST.get('subject_id', '').strip()
        subject_name = request.POST.get('subject_name', '').strip()
        is_active = _posted_is_active(request)

        if not all([subject_id, subject_name]):
            error = "Barcha maydonlarni to'ldiring."
        else:
            try:
                Subject.objects.create(
                    subject_id=subject_id,
                    subject_name=subject_name,
                    is_active=is_active,
                )
                return redirect('subjects:subject_list')
            except IntegrityError:
                error = "Bu Fan ID yoki fan nomi allaqachon mavjud!"

    subjects_queryset = Subject.objects.all()
    paginator = Paginator(subjects_queryset, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'subjects/subject_list.html', {
        'subjects': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'total_subjects': paginator.count,
        'error': error,
    })


@login_required
@require_POST
def update_subject(request, subject_pk):
    subject = get_object_or_404(Subject, pk=subject_pk)
    subject_id = request.POST.get('subject_id', '').strip()
    subject_name = request.POST.get('subject_name', '').strip()
    is_active = _posted_is_active(request)

    if not all([subject_id, subject_name]):
        return JsonResponse({'success': False, 'error': "Barcha maydonlarni to'ldiring."}, status=400)

    duplicate = Subject.objects.exclude(pk=subject.pk).filter(subject_id=subject_id).exists()
    duplicate = duplicate or Subject.objects.exclude(pk=subject.pk).filter(subject_name=subject_name).exists()
    if duplicate:
        return JsonResponse({'success': False, 'error': "Bu Fan ID yoki fan nomi allaqachon mavjud!"}, status=400)

    subject.subject_id = subject_id
    subject.subject_name = subject_name
    subject.is_active = is_active
    subject.save(update_fields=['subject_id', 'subject_name', 'is_active'])

    return JsonResponse({
        'success': True,
        'subject': {
            'id': subject.id,
            'subject_id': subject.subject_id,
            'subject_name': subject.subject_name,
            'is_active': subject.is_active,
        },
    })


@login_required
@require_POST
def toggle_subject_status(request, subject_pk):
    subject = get_object_or_404(Subject, pk=subject_pk)
    subject.is_active = not subject.is_active
    subject.save(update_fields=['is_active'])
    return JsonResponse({'success': True, 'is_active': subject.is_active})


@login_required
@require_POST
def delete_subject(request, subject_pk):
    subject = get_object_or_404(Subject, pk=subject_pk)
    subject.delete()
    return JsonResponse({'success': True})
