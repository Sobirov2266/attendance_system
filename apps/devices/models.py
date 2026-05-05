from django.core.exceptions import ValidationError
from django.db import models

from apps.rooms.models import Room

from .services.encryption import encrypt_password, decrypt_password


class Device(models.Model):

    DEVICE_TYPES = [
        ('entry', 'KIRISH'),
        ('exit', 'CHIQISH'),
        ('room', 'HONA'),
    ]

    name = models.CharField(max_length=100, unique=True)
    ip_address = models.GenericIPAddressField(unique=True)
    username = models.CharField(max_length=50)
    password = models.TextField()  # encrypted
    device_type = models.CharField(max_length=10, choices=DEVICE_TYPES)
    room = models.OneToOneField(
        Room,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='attendance_device',
        verbose_name='Xona',
        help_text='Faqat «Xona» turidagi qurilmalar uchun. Har bir xonada bitta qurilma.',
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def set_password(self, raw_password):
        self.password = encrypt_password(raw_password)

    def get_password(self):
        return decrypt_password(self.password)

    def clean(self):
        if self.device_type == 'room':
            if not self.room_id:
                raise ValidationError({'room': 'Xona turidagi qurilma uchun xona tanlang.'})
        elif self.room_id:
            raise ValidationError({'room': 'Xona faqat «Xona» turidagi qurilmaga biriktiriladi.'})

    def save(self, *args, **kwargs):
        if self.device_type != 'room':
            self.room = None
        self.full_clean()
        if not self.password.startswith('gAAAA'):
            self.set_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.ip_address})"