# core/encryption.py
from cryptography.fernet import Fernet
from django.conf import settings

key = getattr(settings, "SMTP_ENCRYPTION_KEY", Fernet.generate_key())
fernet = Fernet(key)

def encrypt(value: str) -> str:
    return fernet.encrypt(value.encode()).decode()

def decrypt(value: str) -> str:
    return fernet.decrypt(value.encode()).decode()
