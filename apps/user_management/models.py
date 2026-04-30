from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """
    Foydalanuvchi profilini boshqarish modeli
    """

    # user_id =  models.CharField(max_length=15, blank=True)
    POSITION_CHOICES = [
        ('student', 'Talaba'),
        ('teacher', 'O\'qituvchi'),
        ('guest', 'Mehmon'),
        ('admin', 'Admin'),
        ('stuff', 'Xodim'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=100, verbose_name='Ism')
    last_name = models.CharField(max_length=100, verbose_name='Familya')
    position = models.CharField(
        max_length=50,
        choices=POSITION_CHOICES,
        default='guest',
        verbose_name='Lavozim'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqti')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='O\'zgartirilgan vaqti')
    is_active = models.BooleanField(default=True, verbose_name='Faol')

    class Meta:
        verbose_name = 'Foydalanuvchi Profili'
        verbose_name_plural = 'Foydalanuvchi Profillari'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_position_display()})"