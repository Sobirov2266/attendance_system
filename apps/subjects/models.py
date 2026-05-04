from django.db import models


class Subject(models.Model):
    subject_id = models.CharField(max_length=100, unique=True, verbose_name="Fan ID")
    subject_name = models.CharField(max_length=150, unique=True, verbose_name="Fan nomi")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Fan"
        verbose_name_plural = "Fanlar"
        ordering = ['subject_name']

    def __str__(self):
        return self.subject_name
