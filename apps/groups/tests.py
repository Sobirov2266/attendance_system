from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Group


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
