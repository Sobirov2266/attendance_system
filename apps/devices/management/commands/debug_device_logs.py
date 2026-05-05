from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from apps.devices.models import Device
from apps.devices.services.hikvision_debug import fetch_raw_attendance_logs_debug


class Command(BaseCommand):
    help = 'Debug: fetch raw attendance logs from devices'

    def add_arguments(self, parser):
        parser.add_argument('--device-id', type=int, help='Debug only this device ID')
        parser.add_argument('--minutes', type=int, default=120, help='Fetch logs since N minutes ago')

    def handle(self, *args, **options):
        device_id = options.get('device_id')
        minutes = options['minutes']
        since = timezone.now() - timedelta(minutes=minutes)

        qs = Device.objects.filter(is_active=True)
        if device_id:
            qs = qs.filter(id=device_id)

        for device in qs:
            self.stdout.write(f"=== {device.name} ({device.ip_address}) ===")
            success, err, logs = fetch_raw_attendance_logs_debug(device, since=since)
            if success:
                self.stdout.write(self.style.SUCCESS(f"  {len(logs)} logs found"))
                for log in logs[:5]:  # Show first 5
                    self.stdout.write(f"  {log['timestamp']} {log['employee_id']} {log['direction']}")
                if len(logs) > 5:
                    self.stdout.write(f"  ... and {len(logs)-5} more")
            else:
                self.stdout.write(self.style.ERROR(f"  Error: {err}"))
            self.stdout.write("")
