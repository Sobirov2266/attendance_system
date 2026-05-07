from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta

from apps.devices.models import Device, DeviceLog
from apps.devices.services.hikvision_real import fetch_real_attendance_logs
from apps.user_management.models import UserProfile


class Command(BaseCommand):
    help = 'Import daily attendance logs from Hikvision devices (1 day before)'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=1, help='Import logs from N days ago (default: 1)')
        parser.add_argument('--device-id', type=int, help='Import only from this device ID')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be imported without saving')

    def handle(self, *args, **options):
        days_ago = options['days']
        device_id = options.get('device_id')
        dry_run = options['dry_run']

        tashkent_tz = timezone.get_fixed_timezone(300)
        target_date = timezone.now().astimezone(tashkent_tz) - timedelta(days=days_ago)
        
        # Kun boshidan oxirigacha
        start_time = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        self.stdout.write(f"=== KUNLIK IMPORT: {target_date.strftime('%Y-%m-%d')} ===")
        self.stdout.write(f"Vaqt oralig'i: {start_time} - {end_time}")
        self.stdout.write(f"Dry run: {dry_run}")
        self.stdout.write("")

        qs = Device.objects.filter(is_active=True)
        if device_id:
            qs = qs.filter(id=device_id)

        total_imported = 0
        total_skipped = 0

        for device in qs:
            self.stdout.write(f"--- {device.name} ({device.ip_address}) ---")
            
            success, err, logs = fetch_real_attendance_logs(
                device, 
                start_time=start_time, 
                end_time=end_time
            )
            
            if not success:
                self.stdout.write(self.style.ERROR(f"  Xatolik: {err}"))
                continue

            self.stdout.write(f"  {len(logs)} ta log topildi")

            imported_count = 0
            skipped_count = 0

            for log_data in logs:
                employee_id = log_data['employee_id']
                timestamp = log_data['timestamp']
                
                # Employee_id ni integer ga o'tkazish (00000604 -> 604)
                try:
                    employee_id_int = int(employee_id)
                except ValueError:
                    self.stdout.write(f"  SKIP: Invalid employee_id - {employee_id}")
                    skipped_count += 1
                    continue
                
                # UserProfile ni topish (ais_id orqali - string va integer formatlari)
                user = None
                try:
                    # Avval string formatida qidirish
                    user = UserProfile.objects.get(ais_id=employee_id, is_active=True)
                except UserProfile.DoesNotExist:
                    try:
                        # Integer formatida qidirish
                        user = UserProfile.objects.get(ais_id=str(employee_id_int), is_active=True)
                    except UserProfile.DoesNotExist:
                        self.stdout.write(f"  SKIP: User not found - {employee_id} (int: {employee_id_int})")
                        skipped_count += 1
                        continue

                # Dublikatni tekshirish
                existing = DeviceLog.objects.filter(
                    user=user,
                    device=device,
                    timestamp=timestamp
                ).exists()

                if existing:
                    skipped_count += 1
                    continue

                if dry_run:
                    imported_count += 1
                else:
                    # Timestamp ni Tashkent timezone da saqlash
                    if timezone.is_naive(timestamp):
                        timestamp = timezone.make_aware(timestamp, tashkent_tz)
                    # DeviceLog yaratish
                    DeviceLog.objects.create(
                        user=user,
                        device=device,
                        direction=log_data['direction'],
                        timestamp=timestamp
                    )
                    imported_count += 1

            self.stdout.write(f"  Import qilindi: {imported_count}")
            self.stdout.write(f"  O'tkazildi: {skipped_count}")
            self.stdout.write("")

            total_imported += imported_count
            total_skipped += skipped_count

        self.stdout.write("=== NATIJA ===")
        self.stdout.write(f"Jami import qilindi: {total_imported}")
        self.stdout.write(f"Jami o'tkazildi: {total_skipped}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - Hech narsa saqlanmadi"))
        else:
            self.stdout.write(self.style.SUCCESS("Import tugatildi"))
