from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.user_management.models import UserProfile

from .models import Group, GroupStudent


class GroupTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin', password='pass12345')
        self.client.login(username='admin', password='pass12345')

    def create_group(self, index=1, **overrides):
        data = {
            'group_id': f'GR-{index:02d}',
            'group_name': f'Group {index:02d}',
            'is_active': True,
        }
        data.update(overrides)
        return Group.objects.create(**data)

    def create_user_profile(self, index=1, role=UserProfile.Role.STUDENT):
        return UserProfile.objects.create(
            last_name=f'Familya{index:02d}',
            first_name=f'Ism{index:02d}',
            face_id=f'FACE-GR-{index:02d}',
            ais_id=f'AIS-GR-{index:02d}',
            role=role,
        )

    def test_group_list_is_paginated_and_shows_total(self):
        for index in range(25):
            self.create_group(index)

        response = self.client.get(reverse('groups:group_list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['groups']), 20)
        self.assertEqual(response.context['total_groups'], 25)
        self.assertContains(response, 'Jami: <strong>25</strong> ta guruh', html=True)
        self.assertContains(response, '?page=2')

    def test_create_group_from_list(self):
        response = self.client.post(reverse('groups:group_list'), {
            'group_id': 'CS-101',
            'group_name': 'Computer Science 101',
            'is_active': 'inactive',
        })

        self.assertRedirects(response, reverse('groups:group_list'))
        group = Group.objects.get(group_id='CS-101')
        self.assertEqual(group.group_name, 'Computer Science 101')
        self.assertFalse(group.is_active)

    def test_update_rejects_duplicate_group_id_or_name(self):
        first = self.create_group(1)
        second = self.create_group(2)

        response = self.client.post(reverse('groups:update_group', args=[second.id]), {
            'group_id': first.group_id,
            'group_name': second.group_name,
            'is_active': 'active',
        })

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])

    def test_update_toggle_and_delete_group(self):
        group = self.create_group(1)

        update_response = self.client.post(reverse('groups:update_group', args=[group.id]), {
            'group_id': 'CS-202',
            'group_name': 'Computer Science 202',
            'is_active': 'inactive',
        })
        group.refresh_from_db()

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(group.group_id, 'CS-202')
        self.assertEqual(group.group_name, 'Computer Science 202')
        self.assertFalse(group.is_active)

        toggle_response = self.client.post(reverse('groups:toggle_group_status', args=[group.id]))
        group.refresh_from_db()

        self.assertEqual(toggle_response.status_code, 200)
        self.assertTrue(toggle_response.json()['is_active'])
        self.assertTrue(group.is_active)

        delete_response = self.client.post(reverse('groups:delete_group', args=[group.id]))

        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(Group.objects.filter(id=group.id).exists())

    def test_group_student_allows_only_students(self):
        group = self.create_group(1)
        student = self.create_user_profile(1, UserProfile.Role.STUDENT)
        teacher = self.create_user_profile(2, UserProfile.Role.TEACHER)

        membership = GroupStudent.objects.create(group=group, student=student)

        self.assertTrue(membership.is_active)
        self.assertEqual(group.student_memberships.count(), 1)

        with self.assertRaises(ValidationError):
            GroupStudent.objects.create(group=group, student=teacher)

    def test_group_student_is_unique_per_group_and_student(self):
        group = self.create_group(1)
        student = self.create_user_profile(1)
        GroupStudent.objects.create(group=group, student=student)

        with self.assertRaises(ValidationError):
            GroupStudent.objects.create(group=group, student=student)

    def test_group_students_page_shows_only_unassigned_active_students(self):
        group = self.create_group(1)
        other_group = self.create_group(2)
        available_student = self.create_user_profile(1)
        assigned_student = self.create_user_profile(2)
        inactive_student = self.create_user_profile(3)
        inactive_student.is_active = False
        inactive_student.save(update_fields=['is_active'])
        teacher = self.create_user_profile(4, UserProfile.Role.TEACHER)
        GroupStudent.objects.create(group=other_group, student=assigned_student)

        response = self.client.get(reverse('groups:group_students', args=[group.id]))

        self.assertEqual(response.status_code, 200)
        self.assertIn(available_student, response.context['available_students'])
        self.assertNotIn(assigned_student, response.context['available_students'])
        self.assertNotIn(inactive_student, response.context['available_students'])
        self.assertNotIn(teacher, response.context['available_students'])

    def test_assign_students_to_group(self):
        group = self.create_group(1)
        student = self.create_user_profile(1)

        response = self.client.post(reverse('groups:group_students', args=[group.id]), {
            'students': [str(student.id)],
        })

        self.assertRedirects(response, reverse('groups:group_students', args=[group.id]))
        self.assertTrue(GroupStudent.objects.filter(group=group, student=student, is_active=True).exists())

    def test_reactivate_existing_inactive_group_membership(self):
        group = self.create_group(1)
        student = self.create_user_profile(1)
        membership = GroupStudent.objects.create(group=group, student=student, is_active=False)

        response = self.client.post(reverse('groups:group_students', args=[group.id]), {
            'students': [str(student.id)],
        })
        membership.refresh_from_db()

        self.assertRedirects(response, reverse('groups:group_students', args=[group.id]))
        self.assertTrue(membership.is_active)
