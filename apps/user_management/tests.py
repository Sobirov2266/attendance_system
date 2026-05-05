from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from attendance_system.spreadsheet import build_xlsx

from .models import UserProfile


class UserManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin', password='pass12345')
        self.client.login(username='admin', password='pass12345')

    def create_profile(self, index=1, **overrides):
        data = {
            'last_name': f'Familya{index:02d}',
            'first_name': f'Ism{index:02d}',
            'face_id': f'FACE-{index:02d}',
            'ais_id': f'AIS-{index:02d}',
            'role': UserProfile.Role.STUDENT,
            'is_active': True,
        }
        data.update(overrides)
        return UserProfile.objects.create(**data)

    def test_user_list_is_paginated_by_20_and_shows_total(self):
        for index in range(25):
            self.create_profile(index)

        response = self.client.get(reverse('user_management:user_list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['users']), 20)
        self.assertEqual(response.context['total_users'], 25)
        self.assertContains(response, 'Jami: <strong>25</strong> ta foydalanuvchi', html=True)
        self.assertContains(response, '?page=2')

    def test_create_user_profile_from_list(self):
        response = self.client.post(reverse('user_management:user_list'), {
            'last_name': 'Karimov',
            'first_name': 'Ali',
            'face_id': 'FACE-NEW',
            'ais_id': 'AIS-NEW',
            'role': UserProfile.Role.TEACHER,
            'is_active': 'inactive',
        })

        self.assertRedirects(response, reverse('user_management:user_list'))
        user = UserProfile.objects.get(face_id='FACE-NEW')
        self.assertEqual(user.ais_id, 'AIS-NEW')
        self.assertEqual(user.role, UserProfile.Role.TEACHER)
        self.assertFalse(user.is_active)

    def test_update_rejects_duplicate_face_or_ais_id(self):
        first = self.create_profile(1)
        second = self.create_profile(2)

        response = self.client.post(reverse('user_management:update_user', args=[second.id]), {
            'last_name': second.last_name,
            'first_name': second.first_name,
            'face_id': first.face_id,
            'ais_id': second.ais_id,
            'role': second.role,
            'is_active': 'active',
        })

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])

    def test_update_and_toggle_user_status(self):
        profile = self.create_profile(1)

        update_response = self.client.post(reverse('user_management:update_user', args=[profile.id]), {
            'last_name': 'Valiyev',
            'first_name': 'Vali',
            'face_id': 'FACE-UPDATED',
            'ais_id': 'AIS-UPDATED',
            'role': UserProfile.Role.STAFF,
            'is_active': 'inactive',
        })
        profile.refresh_from_db()

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(profile.get_full_name(), 'Valiyev Vali')
        self.assertEqual(profile.role, UserProfile.Role.STAFF)
        self.assertFalse(profile.is_active)

        toggle_response = self.client.post(reverse('user_management:toggle_user_status', args=[profile.id]))
        profile.refresh_from_db()

        self.assertEqual(toggle_response.status_code, 200)
        self.assertTrue(toggle_response.json()['is_active'])
        self.assertTrue(profile.is_active)

    def test_update_teacher_can_attach_login_credentials(self):
        teacher = self.create_profile(
            10,
            role=UserProfile.Role.TEACHER,
            face_id='FACE-T-10',
            ais_id='AIS-T-10',
        )

        response = self.client.post(reverse('user_management:update_user', args=[teacher.id]), {
            'last_name': teacher.last_name,
            'first_name': teacher.first_name,
            'face_id': teacher.face_id,
            'ais_id': teacher.ais_id,
            'role': UserProfile.Role.TEACHER,
            'is_active': 'active',
            'login_username': 'teacher10',
            'login_password': 'pass12345',
        })
        teacher.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(teacher.auth_user_id)
        self.assertEqual(teacher.auth_user.username, 'teacher10')
        self.assertTrue(teacher.auth_user.check_password('pass12345'))
        self.assertEqual(response.json()['user']['login_username'], 'teacher10')

    def test_update_teacher_rejects_duplicate_login_username(self):
        existing_auth = User.objects.create_user(username='teacher-dup', password='pass12345')
        teacher = self.create_profile(
            11,
            role=UserProfile.Role.TEACHER,
            face_id='FACE-T-11',
            ais_id='AIS-T-11',
        )
        teacher.auth_user = existing_auth
        teacher.save(update_fields=['auth_user'])
        another_teacher = self.create_profile(
            12,
            role=UserProfile.Role.TEACHER,
            face_id='FACE-T-12',
            ais_id='AIS-T-12',
        )

        response = self.client.post(reverse('user_management:update_user', args=[another_teacher.id]), {
            'last_name': another_teacher.last_name,
            'first_name': another_teacher.first_name,
            'face_id': another_teacher.face_id,
            'ais_id': another_teacher.ais_id,
            'role': UserProfile.Role.TEACHER,
            'is_active': 'active',
            'login_username': 'teacher-dup',
            'login_password': 'pass12345',
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Bu login allaqachon band.')

    def test_importing_legacy_signals_does_not_create_profile_for_auth_user(self):
        import apps.user_management.signals  # noqa: F401

        User.objects.create_user(username='plain-user')

        self.assertEqual(UserProfile.objects.count(), 0)

    def test_download_student_template(self):
        response = self.client.get(reverse('user_management:download_student_template'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_import_students_from_excel(self):
        excel_bytes = build_xlsx(
            ['Face ID', 'AIS ID', 'Familya', 'Ism', 'Holati'],
            [['FACE-900', 'AIS-900', 'Testov', 'Talaba', 'Faol']],
            sheet_name='Talabalar',
        )
        upload = SimpleUploadedFile(
            'students.xlsx',
            excel_bytes,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

        response = self.client.post(
            reverse('user_management:import_students'),
            {'file': upload},
        )

        self.assertRedirects(response, reverse('user_management:student_list'))
        student = UserProfile.objects.get(face_id='FACE-900')
        self.assertEqual(student.ais_id, 'AIS-900')
        self.assertEqual(student.role, UserProfile.Role.STUDENT)
        self.assertTrue(student.is_active)
