from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.user_management.models import UserProfile


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


class GroupStudent(models.Model):
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='student_memberships',
        verbose_name="Guruh",
    )
    student = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='group_memberships',
        verbose_name="Talaba",
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Guruh talabasi"
        verbose_name_plural = "Guruh talabalari"
        ordering = ['group__group_name', 'student__last_name', 'student__first_name']
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'student'],
                name='unique_group_student_membership',
            ),
            models.UniqueConstraint(
                fields=['student'],
                condition=Q(is_active=True),
                name='unique_active_group_per_student',
            ),
        ]

    def clean(self):
        if self.student_id and self.student.role != UserProfile.Role.STUDENT:
            raise ValidationError({"student": "Guruhga faqat talaba biriktiriladi."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.group} - {self.student}"
