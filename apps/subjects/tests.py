from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from attendance_system.spreadsheet import build_xlsx

from .models import Subject


class SubjectTests(TestCase):
    def setUp(self):
        User.objects.create_user(username='admin', password='pass12345')
        self.client.login(username='admin', password='pass12345')

    def test_import_subjects_from_excel(self):
        excel_bytes = build_xlsx(
            ['Fan ID', 'Fan nomi', 'Holati'],
            [['PHYS-101', 'Fizika', 'Faol']],
            sheet_name='Fanlar',
        )
        upload = SimpleUploadedFile(
            'subjects.xlsx',
            excel_bytes,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

        response = self.client.post(reverse('subjects:import_subjects'), {'file': upload})

        self.assertRedirects(response, reverse('subjects:subject_list'))
        subject = Subject.objects.get(subject_id='PHYS-101')
        self.assertEqual(subject.subject_name, 'Fizika')
        self.assertTrue(subject.is_active)
