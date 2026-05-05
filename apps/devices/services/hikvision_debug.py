import requests
from requests.auth import HTTPDigestAuth
from django.utils import timezone
from datetime import datetime
from django.db import models
from apps.user_management.models import UserProfile
from apps.devices.models import DeviceLog


def fetch_raw_attendance_logs_debug(device, since=None):
    """
    Hikvision qurilmasidan o'tish loglarini olish, debug ma'lumotlar bilan.
    """
    # Qurilma qaysi API endpoint-larini qo'llab-quvvatlashini tekshirish
    base_url = f"http://{device.ip_address}/ISAPI/AccessControl/capabilities"
    headers = {'Content-Type': 'application/xml'}

    try:
        resp = requests.get(
            base_url,
            headers=headers,
            auth=HTTPDigestAuth(device.username, device.get_password()),
            timeout=15
        )
        print(f"[{device.name}] Status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"[{device.name}] Response: {resp.text[:500]}")
            return False, f"API error {resp.status_code}", []

        print(f"[{device.name}] Capabilities response: {resp.text[:800]}")
        # Bu endpoint loglarni bermaydi, faqat qurilma imkoniyatlari
        # Endi boshqa endpoint-larni sinab ko'ramiz
        return try_alternative_endpoints(device, since)

    except Exception as e:
        print(f"[{device.name}] Exception: {e}")
        return False, f"Xatolik: {e}", []


def try_alternative_endpoints(device, since=None):
    """Alternative Hikvision endpoint-larini sinab ko'rish."""
    endpoints = [
        "/ISAPI/AccessControl/attendanceRecord",
        "/ISAPI/AccessControl/attendanceRecord/search",
        "/ISAPI/AccessControl/attendanceRecordInfo",
        "/ISAPI/AccessControl/attendanceInfo",
        "/ISAPI/Event/notification/alertStream",  # Event stream
        "/ISAPI/Event/notification/subscribe",     # Event subscribe
    ]
    
    for endpoint in endpoints:
        url = f"http://{device.ip_address}{endpoint}"
        try:
            resp = requests.get(url, auth=HTTPDigestAuth(device.username, device.get_password()), timeout=10)
            print(f"[{device.name}] {endpoint} -> {resp.status_code}")
            if resp.status_code == 200:
                print(f"[{device.name}] Response preview: {resp.text[:300]}")
                # Parse agar loglar bo'lsa
                return parse_response_if_logs(device, resp.text)
        except Exception as e:
            print(f"[{device.name}] {endpoint} -> Exception: {e}")
    
    return False, "No working endpoint found", []


def parse_response_if_logs(device, xml_text):
    """XML response ni parse qilib, agar loglar bo'lsa qaytarish."""
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_text)
        
        logs = []
        # Har xil tag nomlarini tekshirish
        for tag in ['AttendanceRecord', 'attendanceRecord', 'Record', 'record']:
            for record in root.findall(f'.//{tag}'):
                time_str = record.findtext('time') or record.findtext('Time') or record.findtext('timestamp')
                employee_id = record.findtext('employeeNo') or record.findtext('EmployeeNo') or record.findtext('employeeID')
                direction_raw = record.findtext('direction') or record.findtext('Direction')
                if not time_str or not employee_id:
                    continue
                try:
                    ts = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                except Exception:
                    continue
                direction = 'in' if direction_raw and direction_raw.lower() in ['enter','in'] else 'out'
                logs.append({
                    'device_name': device.name,
                    'employee_id': employee_id,
                    'direction': direction,
                    'timestamp': ts,
                })
        if logs:
            print(f"[{device.name}] Parsed {len(logs)} logs")
            return True, None, logs
        else:
            print(f"[{device.name}] No logs found in XML")
            return False, "No logs in response", []
    except Exception as e:
        print(f"[{device.name}] Parse error: {e}")
        return False, f"Parse error: {e}", []
