from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.devices.models import Device
from apps.devices.services.hikvision_real import fetch_real_attendance_logs


class Command(BaseCommand):
    help = 'Fetch real attendance logs from Hikvision devices (last N hours)'

    def add_arguments(self, parser):
        parser.add_argument('--hours', type=int, default=4, help='Fetch logs from last N hours')
        parser.add_argument('--device-id', type=int, help='Fetch only from this device ID')

    def handle(self, *args, **options):
        hours = options['hours']
        device_id = options.get('device_id')
        
        qs = Device.objects.filter(is_active=True)
        if device_id:
            qs = qs.filter(id=device_id)
        
        total_logs = []
        
        for device in qs:
            self.stdout.write(f"=== {device.name} ({device.ip_address}) ===")
            success, err, logs = fetch_real_attendance_logs(device, hours=hours)
            
            if success:
                self.stdout.write(self.style.SUCCESS(f"  {len(logs)} logs found"))
                for log in logs[:10]:  # Show first 10
                    self.stdout.write(f"  {log['timestamp']} {log['employee_id']} {log['name']}")
                if len(logs) > 10:
                    self.stdout.write(f"  ... and {len(logs)-10} more")
                total_logs.extend(logs)
            else:
                self.stdout.write(self.style.ERROR(f"  Error: {err}"))
            self.stdout.write("")
        
        if total_logs:
            self.stdout.write(self.style.SUCCESS(f"Total: {len(total_logs)} logs from all devices"))
        else:
            self.stdout.write(self.style.WARNING("No logs found"))
