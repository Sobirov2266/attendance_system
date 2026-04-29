from cryptography.fernet import Fernet
from django.conf import settings

# KEY ni settings dan olamiz
def get_cipher():
    return Fernet(settings.ENCRYPTION_KEY)


def encrypt_password(password: str) -> str:
    cipher = get_cipher()
    return cipher.encrypt(password.encode()).decode()


def decrypt_password(encrypted_password: str) -> str:
    cipher = get_cipher()
    return cipher.decrypt(encrypted_password.encode()).decode()