# core/encryption.py
try:
    from cryptography.fernet import Fernet
    from django.conf import settings

    # Use a key from settings if provided, otherwise generate a new key
    key = getattr(settings, "SMTP_ENCRYPTION_KEY", Fernet.generate_key())
    fernet = Fernet(key)

    def encrypt(value: str) -> str:
        """Encrypt a string using Fernet."""
        return fernet.encrypt(value.encode()).decode()

    def decrypt(value: str) -> str:
        """Decrypt a string using Fernet."""
        return fernet.decrypt(value.encode()).decode()

except ImportError:
    # Fallback for development/testing if cryptography is not installed
    def encrypt(value: str) -> str:
        """Mock encryption (returns plaintext)."""
        return value

    def decrypt(value: str) -> str:
        """Mock decryption (returns plaintext)."""
        return value
