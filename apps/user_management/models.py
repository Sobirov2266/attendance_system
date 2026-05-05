from django.conf import settings
from django.db import models


class UserProfile(models.Model):

    class Role(models.TextChoices):
        STUDENT = 'student', 'Talaba'
        TEACHER = 'teacher', "O'qituvchi"
        STAFF   = 'staff',   'Xodim'

    face_id    = models.CharField(max_length=100, unique=True, default='', verbose_name="Face ID")
    ais_id     = models.CharField(max_length=100, unique=True, default='', verbose_name="AIS ID")
    last_name  = models.CharField(max_length=100, verbose_name="Familya")
    first_name = models.CharField(max_length=100, verbose_name="Ism")
    role       = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT, verbose_name="Lavozim")
    auth_user  = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_profile',
        verbose_name='Tizim foydalanuvchisi',
    )
    is_active  = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        ordering            = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

    def get_full_name(self):
        return f"{self.last_name} {self.first_name}"
