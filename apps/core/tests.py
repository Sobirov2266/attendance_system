from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.groups.models import Group
from apps.user_management.models import UserProfile


class DashboardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin', password='pass12345')
        self.client.login(username='admin', password='pass12345')

    def test_dashboard_counts_user_profiles_not_auth_users(self):
        User.objects.create_user(username='second-admin')
        for index in range(21):
            UserProfile.objects.create(
                last_name=f'Familya{index:02d}',
                first_name=f'Ism{index:02d}',
                face_id=f'FACE-{index:02d}',
                ais_id=f'AIS-{index:02d}',
                role=UserProfile.Role.STUDENT,
            )

        response = self.client.get(reverse('core:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user_count'], 21)
        self.assertContains(response, 'data-target="21"')

    def test_dashboard_counts_groups(self):
        Group.objects.create(group_id='G-01', group_name='Group 01')
        Group.objects.create(group_id='G-02', group_name='Group 02', is_active=False)

        response = self.client.get(reverse('core:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['group_count'], 2)

    def test_dashboard_redirects_linked_teacher_to_teacher_panel(self):
        teacher_auth = User.objects.create_user(username='teacher-login', password='pass12345')
        UserProfile.objects.create(
            last_name='Teacher',
            first_name='Panel',
            face_id='FACE-TEACHER-1',
            ais_id='AIS-TEACHER-1',
            role=UserProfile.Role.TEACHER,
            auth_user=teacher_auth,
        )
        self.client.login(username='teacher-login', password='pass12345')

        response = self.client.get(reverse('core:dashboard'))

        self.assertRedirects(response, reverse('schedule:teacher_attendance'))
