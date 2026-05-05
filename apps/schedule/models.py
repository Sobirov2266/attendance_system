from datetime import time

from django.core.exceptions import ValidationError
from django.db import models

from apps.groups.models import Group
from apps.rooms.models import Room
from apps.subjects.models import Subject
from apps.user_management.models import UserProfile


class GroupSubject(models.Model):
    """Guruh uchun fan va uning oqituvchisi."""

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='group_subjects',
        verbose_name='Guruh',
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name='group_offerings',
        verbose_name='Fan',
    )
    teacher = models.ForeignKey(
        UserProfile,
        on_delete=models.PROTECT,
        related_name='teaching_assignments',
        verbose_name="O'qituvchi",
    )
    is_active = models.BooleanField(default=True, verbose_name='Faol')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Guruh fani'
        verbose_name_plural = 'Guruh fanlari'
        ordering = ['group__group_name', 'subject__subject_name']
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'subject'],
                name='unique_group_subject_offering',
            ),
        ]

    def clean(self):
        if self.teacher_id and self.teacher.role != UserProfile.Role.TEACHER:
            raise ValidationError({'teacher': "Faqat o'qituvchi rolli biriktiriladi."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.group} - {self.subject}"


class LessonSlot(models.Model):
    """Haftalik dars sloti: qaysi guruh fani qaysi xonada va qaysi paraga tushadi."""

    class Weekday(models.IntegerChoices):
        MONDAY = 1, 'Dushanba'
        TUESDAY = 2, 'Seshanba'
        WEDNESDAY = 3, 'Chorshanba'
        THURSDAY = 4, 'Payshanba'
        FRIDAY = 5, 'Juma'
        SATURDAY = 6, 'Shanba'

    class LessonNumber(models.IntegerChoices):
        FIRST = 1, '1-para (08:30-09:50)'
        SECOND = 2, '2-para (10:00-11:20)'
        THIRD = 3, '3-para (11:30-12:50)'
        FOURTH = 4, '4-para (13:30-15:50)'
        FIFTH = 5, '5-para (16:00-17:20)'

    LESSON_TIMES = {
        LessonNumber.FIRST: (time(8, 30), time(9, 50)),
        LessonNumber.SECOND: (time(10, 0), time(11, 20)),
        LessonNumber.THIRD: (time(11, 30), time(12, 50)),
        LessonNumber.FOURTH: (time(13, 30), time(15, 50)),
        LessonNumber.FIFTH: (time(16, 0), time(17, 20)),
    }

    group_subject = models.ForeignKey(
        GroupSubject,
        on_delete=models.CASCADE,
        related_name='lesson_slots',
        verbose_name='Guruh fani',
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name='lesson_slots',
        verbose_name='Xona',
    )
    weekday = models.PositiveSmallIntegerField(
        choices=Weekday.choices,
        verbose_name='Hafta kuni',
    )
    lesson_number = models.PositiveSmallIntegerField(
        choices=LessonNumber.choices,
        default=LessonNumber.FIRST,
        verbose_name='Para',
    )
    start_time = models.TimeField(verbose_name='Boshlanish', editable=False)
    end_time = models.TimeField(verbose_name='Tugash', editable=False)
    is_active = models.BooleanField(default=True, verbose_name='Faol')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Dars sloti'
        verbose_name_plural = 'Dars slotlari'
        ordering = ['weekday', 'lesson_number', 'group_subject__group__group_name']

    def clean(self):
        if self.lesson_number and self.lesson_number not in self.LESSON_TIMES:
            raise ValidationError({'lesson_number': "Para noto'g'ri tanlangan."})
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("Tugash vaqti boshlanishdan keyin bo'lishi kerak.")

    def set_lesson_times(self):
        self.start_time, self.end_time = self.LESSON_TIMES[self.lesson_number]

    def save(self, *args, **kwargs):
        self.set_lesson_times()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        wd = self.get_weekday_display()
        st = self.start_time.strftime('%H:%M')
        et = self.end_time.strftime('%H:%M')
        return f'{wd} {self.lesson_number}-para {st}-{et} | {self.group_subject} | {self.room}'
