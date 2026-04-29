from django.db import models
from .services.encryption import encrypt_password, decrypt_password



# face id malumotlarini kiritish
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
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)


    def set_password(self, raw_password):
        self.password = encrypt_password(raw_password)


    def get_password(self):
        return decrypt_password(self.password)



    def save(self, *args, **kwargs):
        # agar password allaqachon encrypted bo‘lmasa
        if not self.password.startswith("gAAAA"):
            self.set_password(self.password)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.ip_address})"