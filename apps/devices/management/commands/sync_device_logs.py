from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from apps.devices.models import Device
from apps.devices.services.hikvision import fetch_attendance_logs


class Command(BaseCommand):
    help = 'Sync attendance logs from active Hikvision devices'

    def add_arguments(self, parser):
        parser.add_argument('--device-id', type=int, help='Sync only this device ID')
        parser.add_argument('--minutes', type=int, default=10, help='Fetch logs since N minutes ago')

    def handle(self, *args, **options):
        device_id = options.get('device_id')
        minutes = options['minutes']
        since = timezone.now() - timedelta(minutes=minutes)

        qs = Device.objects.filter(is_active=True)
        if device_id:
            qs = qs.filter(id=device_id)

        for device in qs:
            self.stdout.write(f"Syncing {device.name} ({device.ip_address})...")
            success, msg = fetch_attendance_logs(device, since=since)
            if success:
                self.stdout.write(self.style.SUCCESS(f"  {msg}"))
            else:
                self.stdout.write(self.style.ERROR(f"  Error: {msg}"))

        self.stdout.write(self.style.SUCCESS("Sync complete."))
