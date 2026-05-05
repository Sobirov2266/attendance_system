from datetime import datetime, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.devices.models import Device, DeviceLog
from apps.groups.models import Group
from apps.groups.models import GroupStudent
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

    def test_teacher_attendance_list_requires_linked_teacher(self):
        response = self.client.get(reverse('schedule:teacher_attendance'))
        self.assertEqual(response.status_code, 403)

        teacher_auth = User.objects.create_user(username='teacher1', password='pass12345')
        self.teacher.auth_user = teacher_auth
        self.teacher.save(update_fields=['auth_user'])
        self.client.login(username='teacher1', password='pass12345')
        response = self.client.get(reverse('schedule:teacher_attendance'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.group.group_name)
        self.assertContains(response, self.subject.subject_name)

    def test_teacher_attendance_detail_shows_missing_room_device_message(self):
        teacher_auth = User.objects.create_user(username='teacher2', password='pass12345')
        self.teacher.auth_user = teacher_auth
        self.teacher.save(update_fields=['auth_user'])
        self.client.login(username='teacher2', password='pass12345')

        LessonSlot.objects.create(
            group_subject=self.group_subject,
            room=self.room,
            weekday=timezone.localdate().isoweekday(),
            lesson_number=LessonSlot.LessonNumber.FIRST,
        )
        student = UserProfile.objects.create(
            face_id='S-100',
            ais_id='AIS-S-100',
            last_name='Talaba',
            first_name='Bir',
            role=UserProfile.Role.STUDENT,
        )
        GroupStudent.objects.create(group=self.group, student=student, is_active=True)

        response = self.client.get(
            reverse('schedule:teacher_attendance_detail', args=[self.group_subject.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Xonaga device biriktirilmagan")
        self.assertContains(response, student.get_full_name())

    def test_teacher_attendance_detail_shows_university_and_lesson_presence(self):
        teacher_auth = User.objects.create_user(username='teacher3', password='pass12345')
        self.teacher.auth_user = teacher_auth
        self.teacher.save(update_fields=['auth_user'])
        self.client.login(username='teacher3', password='pass12345')

        today = timezone.localdate()
        LessonSlot.objects.create(
            group_subject=self.group_subject,
            room=self.room,
            weekday=today.isoweekday(),
            lesson_number=LessonSlot.LessonNumber.FIRST,
        )
        room_device = Device.objects.create(
            name='Room Device 01',
            ip_address='10.10.10.10',
            username='admin',
            password='12345',
            device_type='room',
            room=self.room,
            is_active=True,
        )
        entry_device = Device.objects.create(
            name='Entry Device 01',
            ip_address='10.10.10.11',
            username='admin',
            password='12345',
            device_type='entry',
            is_active=True,
        )

        student_present = UserProfile.objects.create(
            face_id='S-200',
            ais_id='AIS-S-200',
            last_name='Talaba',
            first_name='Keldi',
            role=UserProfile.Role.STUDENT,
        )
        student_absent = UserProfile.objects.create(
            face_id='S-201',
            ais_id='AIS-S-201',
            last_name='Talaba',
            first_name='Kelmagan',
            role=UserProfile.Role.STUDENT,
        )
        GroupStudent.objects.create(group=self.group, student=student_present, is_active=True)
        GroupStudent.objects.create(group=self.group, student=student_absent, is_active=True)

        tashkent_tz = timezone.get_fixed_timezone(300)
        day = timezone.localtime(timezone.now(), tashkent_tz).date()
        entry_time = timezone.make_aware(
            datetime.combine(day, time(8, 45)),
            tashkent_tz,
        )
        lesson_time = timezone.make_aware(
            datetime.combine(day, time(8, 40)),
            tashkent_tz,
        )
        DeviceLog.objects.create(
            user=student_present,
            device=entry_device,
            direction='in',
            timestamp=entry_time,
        )
        DeviceLog.objects.create(
            user=student_present,
            device=room_device,
            direction='in',
            timestamp=lesson_time,
        )

        response = self.client.get(
            reverse('schedule:teacher_attendance_detail', args=[self.group_subject.id]),
            {'date': day.strftime('%Y-%m-%d')},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, student_present.get_full_name())
        self.assertContains(response, student_absent.get_full_name())
        self.assertContains(response, 'Active (Room Device 01)')
