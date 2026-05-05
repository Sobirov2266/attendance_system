import requests
from requests.auth import HTTPDigestAuth
from datetime import datetime, timedelta, timezone as dt_timezone
from django.utils import timezone


def fetch_real_attendance_logs(device, hours=4, start_time=None, end_time=None):
    """
    Hikvision parkovka turniketi uchun real loglarni olish (AcsEvent API).
    Oxirgi N soatdagi barcha o'tishlarni qaytaradi.
    """
    url = f"http://{device.ip_address}/ISAPI/AccessControl/AcsEvent?format=json"
    
    # Qurilma bilan mos format (+05:00) yuborish
    device_tz = dt_timezone(timedelta(hours=5))
    if start_time is not None and end_time is not None:
        if timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time, timezone.get_current_timezone())
        if timezone.is_naive(end_time):
            end_time = timezone.make_aware(end_time, timezone.get_current_timezone())
        start_time = timezone.localtime(start_time, device_tz)
        end_time = timezone.localtime(end_time, device_tz)
    else:
        end_time = timezone.now().astimezone(device_tz)
        start_time = end_time - timedelta(hours=hours)
    
    start_str = start_time.isoformat(timespec='seconds')
    end_str = end_time.isoformat(timespec='seconds')
    
    all_events = []
    position = 0
    
    try:
        while True:
            data = {
                "AcsEventCond": {
                    "searchID": "1",
                    "searchResultPosition": position,
                    "maxResults": 100,  # Ko'proq olish
                    "major": 5,        # AccessControl event
                    "minor": 0,        # Barcha minor eventlar
                    "startTime": start_str,
                    "endTime": end_str
                }
            }
            
            response = requests.post(
                url,
                json=data,
                auth=HTTPDigestAuth(device.username, device.get_password()),
                timeout=15
            )
            
            if response.status_code != 200:
                return False, f"API error {response.status_code}", []
            
            result = response.json()
            
            if "AcsEvent" not in result:
                print(f"[{device.name}] API response:", result)
                break
            
            events = result["AcsEvent"].get("InfoList", [])
            if not events:
                break
            
            all_events.extend(events)
            
            # MORE bo'lmasa to'xtatish
            if result["AcsEvent"].get("responseStatusStrg") != "MORE":
                break
            
            position += len(events)
        
        # Filter: minor=75 (normal o'tish)
        logs = []
        for event in all_events:
            if event.get("minor") == 75:  # Normal access granted
                employee_id = event.get("employeeNoString", "")
                name = event.get("name", "")
                time_str = event.get("time", "")
                
                if not employee_id or not time_str:
                    continue
                
                try:
                    # Vaqtni parse qilish
                    ts = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                except Exception:
                    continue
                
                logs.append({
                    'device_name': device.name,
                    'employee_id': employee_id,
                    'name': name,
                    'timestamp': ts,
                    'direction': 'in',  # Parkovka odatda kirish hisoblanadi
                })
        
        print(f"[{device.name}] Found {len(logs)} logs in last {hours} hours")
        return True, None, logs
        
    except Exception as e:
        print(f"[{device.name}] Exception: {e}")
        return False, f"Xatolik: {e}", []
