from django.db import models


class Group(models.Model):
    group_id = models.CharField(max_length=100, unique=True, verbose_name="Group ID")
    group_name = models.CharField(max_length=150, unique=True, verbose_name="Guruh nomi")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Guruh"
        verbose_name_plural = "Guruhlar"
        ordering = ['group_name']

    def __str__(self):
        return self.group_name
