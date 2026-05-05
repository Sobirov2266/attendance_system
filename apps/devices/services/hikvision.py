import requests
from requests.auth import HTTPDigestAuth
from django.utils import timezone
from datetime import datetime

from django.db import models
from apps.user_management.models import UserProfile
from apps.devices.models import DeviceLog


def check_device_connection(ip, username, password):
    url = f"http://{ip}/ISAPI/System/deviceInfo"

    try:
        response = requests.get(
            url,
            auth=HTTPDigestAuth(username, password),
            timeout=5
        )

        if response.status_code == 200:
            return True, None
        else:
            return False, "Login yoki parol noto‘g‘ri"

    except requests.exceptions.ConnectTimeout:
        return False, "Qurilmaga ulanish vaqti tugadi"

    except requests.exceptions.ConnectionError:
        return False, "Qurilma topilmadi yoki tarmoqda yo‘q"

    except Exception as e:
        return False, str(e)


def fetch_attendance_logs(device, since=None):
    """
    Hikvision qurilmasidan o'tish loglarini olib, DeviceLog yozuvlarini yaratadi.
    since: datetime (UTC) — shu vaqtdan keyingi loglarni oladi
    """
    base_url = f"http://{device.ip_address}/ISAPI/AccessControl/attendanceRecord/search"
    headers = {'Content-Type': 'application/xml'}

    # XML so‘rov (Hikvision Attendance API)
    xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
<AttendanceRecordSearchCond>
    <searchResultPosition>0</searchResultPosition>
    <maxRecords>200</maxRecords>
</AttendanceRecordSearchCond>"""

    try:
        resp = requests.post(
            base_url,
            data=xml_payload.encode('utf-8'),
            headers=headers,
            auth=HTTPDigestAuth(device.username, device.get_password()),
            timeout=10
        )
        if resp.status_code != 200:
            return False, f"API error {resp.status_code}"

        # XML parse (soddalashtirilgan)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.text)

        created = 0
        for record in root.findall('.//AttendanceRecord'):
            # Vaqt
            time_str = record.findtext('time')
            if time_str:
                try:
                    # Hikvision format: 2026-05-05T09:30:00+05:00
                    ts = datetime.fromisoformat(time_str)
                except Exception:
                    continue
            else:
                continue

            # Foydalanuvchi ID ( AIS ID yoki Face ID )
            employee_id = record.findtext('employeeNo')
            if not employee_id:
                continue

            # Yo'nalish (in/out)
            direction_raw = record.findtext('direction', '').lower()
            direction = 'in' if direction_raw == 'enter' else 'out'

            # Bazadan foydalanuvchini topish
            user = UserProfile.objects.filter(
                models.Q(ais_id=employee_id) | models.Q(face_id=employee_id),
                is_active=True
            ).first()
            if not user:
                continue

            # Log yaratish (duplicate oldini olish)
            log, created_log = DeviceLog.objects.get_or_create(
                user=user,
                device=device,
                timestamp=ts,
                direction=direction,
                defaults={'created_at': timezone.now()}
            )
            if created_log:
                created += 1

        return True, f"{created} ta yangi log qo‘shildi."

    except Exception as e:
        return False, f"Xatolik: {e}"


def fetch_raw_attendance_logs(device, since=None):
    """
    Hikvision qurilmasidan o'tish loglarini olib, raw ma'lumot sifatida qaytaradi.
    Bazaga yozmaydi. Monitoring uchun.
    """
    base_url = f"http://{device.ip_address}/ISAPI/AccessControl/attendanceRecord/search"
    headers = {'Content-Type': 'application/xml'}

    xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
<AttendanceRecordSearchCond>
    <searchResultPosition>0</searchResultPosition>
    <maxRecords>500</maxRecords>
</AttendanceRecordSearchCond>"""

    try:
        resp = requests.post(
            base_url,
            data=xml_payload.encode('utf-8'),
            headers=headers,
            auth=HTTPDigestAuth(device.username, device.get_password()),
            timeout=10
        )
        if resp.status_code != 200:
            return False, f"API error {resp.status_code}", []

        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.text)

        logs = []
        for record in root.findall('.//AttendanceRecord'):
            time_str = record.findtext('time')
            employee_id = record.findtext('employeeNo')
            direction_raw = record.findtext('direction', '').lower()
            if not time_str or not employee_id:
                continue
            try:
                ts = datetime.fromisoformat(time_str)
            except Exception:
                continue
            direction = 'in' if direction_raw == 'enter' else 'out'
            logs.append({
                'device_name': device.name,
                'employee_id': employee_id,
                'direction': direction,
                'timestamp': ts,
            })
        return True, None, logs

    except Exception as e:
        return False, f"Xatolik: {e}", []