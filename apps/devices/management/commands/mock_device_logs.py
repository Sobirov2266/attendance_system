from django.core.management.base import BaseCommand
from django.utils import timezone
import random
from datetime import datetime, timedelta

from apps.devices.models import Device, DeviceLog
from apps.user_management.models import UserProfile


class Command(BaseCommand):
    help = 'Create mock device logs for testing monitoring'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=20, help='Number of logs to create')
        parser.add_argument('--days', type=int, default=3, help='Number of days back to generate logs')

    def handle(self, *args, **options):
        count = options['count']
        days = options['days']

        devices = list(Device.objects.filter(is_active=True))
        users = list(UserProfile.objects.filter(role=UserProfile.Role.STUDENT))

        if not devices:
            self.stdout.write(self.style.ERROR('No active devices found.'))
            return
        if not users:
            self.stdout.write(self.style.ERROR('No students found.'))
            return

        created = 0
        now = timezone.now()

        for i in range(count):
            # Random time within last N days
            random_hours = random.uniform(0, days * 24)
            timestamp = now - timedelta(hours=random_hours)

            device = random.choice(devices)
            user = random.choice(users)
            direction = random.choice(['in', 'out'])

            DeviceLog.objects.get_or_create(
                user=user,
                device=device,
                timestamp=timestamp,
                direction=direction,
                defaults={'created_at': now}
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created} mock device logs.'))
