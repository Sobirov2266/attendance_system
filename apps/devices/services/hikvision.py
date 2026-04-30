import requests
from requests.auth import HTTPDigestAuth


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