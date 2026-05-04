from django.db import models


class Room(models.Model):
    room_id = models.CharField(max_length=100, unique=True, verbose_name="Xona ID")
    room_name = models.CharField(max_length=150, unique=True, verbose_name="Xona nomi")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Xona"
        verbose_name_plural = "Xonalar"
        ordering = ['room_name']

    def __str__(self):
        return self.room_name
