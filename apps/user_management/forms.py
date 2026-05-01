from django import forms

from .models import UserProfile


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['last_name', 'first_name', 'face_id', 'ais_id', 'role', 'is_active']
        widgets = {
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Familya',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ism',
            }),
            'face_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'HIK-00123',
            }),
            'ais_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'AIS-45678',
            }),
            'role': forms.Select(attrs={
                'class': 'form-control',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }


class UserFilterForm(forms.Form):
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "Ism, familya, Face ID yoki AIS ID bo'yicha qidiring",
        }),
        label='Qidirish',
    )
    role = forms.ChoiceField(
        required=False,
        choices=[('', '--- Barcha lavozimlar ---')] + list(UserProfile.Role.choices),
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Lavozim',
    )
    is_active = forms.ChoiceField(
        required=False,
        choices=[('', '--- Barcha holat ---'), ('active', 'Faol'), ('inactive', 'Nofaol')],
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Holat',
    )
