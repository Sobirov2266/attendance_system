from datetime import time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.groups.models import Group
from apps.rooms.models import Room
from apps.subjects.models import Subject
from apps.user_management.models import UserProfile

from .models import GroupSubject, LessonSlot


class LessonSlotTests(TestCase):
    def setUp(self):
        User.objects.create_user(username='admin', password='pass12345')
        self.client.login(username='admin', password='pass12345')

        self.group = Group.objects.create(group_id='G-01', group_name='Group 01')
        self.subject = Subject.objects.create(subject_id='S-01', subject_name='Math')
        self.teacher = UserProfile.objects.create(
            face_id='T-01',
            ais_id='AIS-T-01',
            last_name='Teacher',
            first_name='One',
            role=UserProfile.Role.TEACHER,
        )
        self.group_subject = GroupSubject.objects.create(
            group=self.group,
            subject=self.subject,
            teacher=self.teacher,
        )
        self.room = Room.objects.create(room_id='R-01', room_name='Room 01')

    def test_lesson_slot_sets_times_from_lesson_number(self):
        slot = LessonSlot.objects.create(
            group_subject=self.group_subject,
            room=self.room,
            weekday=LessonSlot.Weekday.MONDAY,
            lesson_number=LessonSlot.LessonNumber.SECOND,
        )

        self.assertEqual(slot.start_time, time(10, 0))
        self.assertEqual(slot.end_time, time(11, 20))

    def test_create_lesson_slot_from_view_uses_lesson_number(self):
        response = self.client.post(reverse('schedule:lesson_slot_list'), {
            'group_subject': str(self.group_subject.id),
            'room': str(self.room.id),
            'weekday': str(LessonSlot.Weekday.TUESDAY),
            'lesson_number': str(LessonSlot.LessonNumber.FOURTH),
            'is_active': 'active',
        })

        self.assertRedirects(response, reverse('schedule:lesson_slot_list'))
        slot = LessonSlot.objects.get()
        self.assertEqual(slot.lesson_number, LessonSlot.LessonNumber.FOURTH)
        self.assertEqual(slot.start_time, time(13, 30))
        self.assertEqual(slot.end_time, time(15, 50))

    def test_update_lesson_slot_recalculates_times(self):
        slot = LessonSlot.objects.create(
            group_subject=self.group_subject,
            room=self.room,
            weekday=LessonSlot.Weekday.MONDAY,
            lesson_number=LessonSlot.LessonNumber.FIRST,
        )

        response = self.client.post(reverse('schedule:update_lesson_slot', args=[slot.id]), {
            'group_subject': str(self.group_subject.id),
            'room': str(self.room.id),
            'weekday': str(LessonSlot.Weekday.WEDNESDAY),
            'lesson_number': str(LessonSlot.LessonNumber.FIFTH),
            'is_active': 'inactive',
        })
        slot.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(slot.lesson_number, LessonSlot.LessonNumber.FIFTH)
        self.assertEqual(slot.start_time, time(16, 0))
        self.assertEqual(slot.end_time, time(17, 20))
        self.assertFalse(slot.is_active)
