from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from attendance_system.spreadsheet import build_xlsx

from .models import Room


class RoomTests(TestCase):
    def setUp(self):
        User.objects.create_user(username='admin', password='pass12345')
        self.client.login(username='admin', password='pass12345')

    def test_import_rooms_from_excel(self):
        excel_bytes = build_xlsx(
            ['Xona ID', 'Xona nomi', 'Holati'],
            [['B-202', 'Laboratoriya B', 'Faol']],
            sheet_name='Xonalar',
        )
        upload = SimpleUploadedFile(
            'rooms.xlsx',
            excel_bytes,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

        response = self.client.post(reverse('rooms:import_rooms'), {'file': upload})

        self.assertRedirects(response, reverse('rooms:room_list'))
        room = Room.objects.get(room_id='B-202')
        self.assertEqual(room.room_name, 'Laboratoriya B')
        self.assertTrue(room.is_active)
