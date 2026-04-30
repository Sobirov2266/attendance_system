from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import UserProfile
from .forms import UserProfileForm, UserFilterForm


def is_admin(user):
    """
    Foydalanuvchi admin ekanligini tekshirish
    """
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_admin)
def user_list(request):
    """
    Foydalanuvchilar ro'yxatini ko'rish
    """

    users = User.objects.all().select_related('profile')
    filter_form = UserFilterForm(request.GET)

    # Qidirish
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(profile__first_name__icontains=search_query) |
            Q(profile__last_name__icontains=search_query) |
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Lavozim bo'yicha filtrlash
    position = request.GET.get('position', '')
    if position:
        users = users.filter(profile__position=position)

    # Holat bo'yicha filtrlash
    is_active = request.GET.get('is_active', '')
    if is_active == 'active':
        users = users.filter(profile__is_active=True)
    elif is_active == 'inactive':
        users = users.filter(profile__is_active=False)

    # Pagination
    paginator = Paginator(users, 10)  # 10 ta foydalanuvchi har bir sahifada
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'users': page_obj.object_list,
        'filter_form': filter_form,
        'search_query': search_query,
        'total_users': paginator.count
    }

    return render(request, 'user_management/user_list.html', context)


@login_required
@user_passes_test(is_admin)
def user_create(request):
    """
    Yangi foydalanuvchi yaratish
    """
    if request.method == 'POST':
        form = UserProfileForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            position = form.cleaned_data.get('position')
            is_active = form.cleaned_data.get('is_active')

            # Yangi User yaratish
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name
            )

            # UserProfile yaratish
            UserProfile.objects.create(
                user=user,
                first_name=first_name,
                last_name=last_name,
                position=position,
                is_active=is_active
            )

            messages.success(
                request,
                f'{first_name} {last_name} muvaffaqiyatli qo\'shildi!'
            )
            return redirect('user_list')
    else:
        form = UserProfileForm()

    context = {'form': form, 'title': 'Yangi Foydalanuvchi Qo\'shish'}
    return render(request, 'user_management/user_form.html', context)


@login_required
@user_passes_test(is_admin)
def user_edit(request, user_id):
    """
    Foydalanuvchi ma'lumotlarini tahrirlash
    """
    user = get_object_or_404(User, pk=user_id)
    profile = get_object_or_404(UserProfile, user=user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')

            # User ma'lumotlarini yangilash
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.save()

            # Profile ma'lumotlarini yangilash
            form.save()

            messages.success(
                request,
                f'{first_name} {last_name} ma\'lumotlari yangilandi!'
            )
            return redirect('user_list')
    else:
        initial_data = {
            'username': user.username,
            'email': user.email,
        }
        form = UserProfileForm(instance=profile, initial=initial_data)

    context = {
        'form': form,
        'user': user,
        'title': f'{user.first_name} {user.last_name} - Tahrirlash'
    }
    return render(request, 'user_management/user_form.html', context)


@login_required
@user_passes_test(is_admin)
def user_delete(request, user_id):
    """
    Foydalanuvchini o'chirish
    """
    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        name = f'{user.first_name} {user.last_name}'
        user.delete()
        messages.success(request, f'{name} muvaffaqiyatli o\'chirildi!')
        return redirect('user_list')

    context = {'user': user}
    return render(request, 'user_management/user_confirm_delete.html', context)


@login_required
@user_passes_test(is_admin)
def user_detail(request, user_id):
    """
    Foydalanuvchi tafsilotlarini ko'rish
    """
    user = get_object_or_404(User, pk=user_id)
    profile = get_object_or_404(UserProfile, user=user)

    context = {
        'user': user,
        'profile': profile
    }
    return render(request, 'user_management/user_detail.html', context)


@login_required
def my_profile(request):
    """
    Kendi profilini ko'rish
    """
    user = request.user
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(
            user=user,
            first_name=user.first_name or user.username,
            last_name=user.last_name or ''
        )

    context = {
        'user': user,
        'profile': profile
    }
    return render(request, 'user_management/my_profile.html', context)