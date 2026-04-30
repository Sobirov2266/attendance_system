from django import forms
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileForm(forms.ModelForm):
    """
    Foydalanuvchi profili formasi
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Foydalanuvchi nomi'
        }),
        help_text='Hali foydalanilmagan nomi kiriting'
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email manzili'
        }),
        required=False
    )

    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'position', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ism'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Familya'
            }),
            'position': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].label = 'Ism'
        self.fields['last_name'].label = 'Familya'
        self.fields['position'].label = 'Lavozim'
        self.fields['is_active'].label = 'Faol'

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if self.instance.pk:
            # Tahrirlash paytida
            if User.objects.filter(username=username).exclude(pk=self.instance.user.pk).exists():
                raise forms.ValidationError('Bu foydalanuvchi nomi allaqachon mavjud')
        else:
            # Yangi yaratish paytida
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError('Bu foydalanuvchi nomi allaqachon mavjud')
        return username


class UserFilterForm(forms.Form):
    """
    Foydalanuvchilarni filtrlash formasi
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ism, familya yoki username bo\'yicha qidiring'
        }),
        label='Qidirish'
    )
    position = forms.ChoiceField(
        required=False,
        choices=[('', '--- Barcha lavozimlar ---')] + UserProfile.POSITION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Lavozim'
    )
    is_active = forms.ChoiceField(
        required=False,
        choices=[('', '--- Barcha holat ---'), ('active', 'Faol'), ('inactive', 'Nofaol')],
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Holat'
    )