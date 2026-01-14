# core/encryption.py
import base64
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import logging

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    # Get encryption key from settings or use a default for development
    def get_encryption_key():
        """Get the encryption key from settings or generate a consistent one."""
        
        # First try to get from settings
        key = getattr(settings, 'ENCRYPTION_KEY', None)
        
        if key:
            # Ensure it's bytes
            if isinstance(key, str):
                key = key.encode()
            # Ensure it's 32 bytes base64 encoded
            if len(key) != 44:  # Fernet key is 32 bytes urlsafe base64 encoded
                # Derive a key from the provided string
                password = key if isinstance(key, bytes) else key.encode()
                salt = b'signalry_salt_'  # Use a consistent salt
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(password))
            return key
        else:
            # For development, generate a consistent key
            # WARNING: In production, you MUST set ENCRYPTION_KEY in settings
            password = b'signalry_default_key_do_not_use_in_production'
            salt = b'signalry_salt_'
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            return base64.urlsafe_b64encode(kdf.derive(password))
    
    # Get the key and create Fernet instance
    key = get_encryption_key()
    fernet = Fernet(key)

    def encrypt(value: str) -> str:
        """Encrypt a string using Fernet."""
        if not value:
            return ""
        try:
            if isinstance(value, str):
                value = value.encode('utf-8')
            encrypted = fernet.encrypt(value)
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(value: str) -> str:
        """Decrypt a string using Fernet."""
        if not value:
            return ""
        try:
            if isinstance(value, str):
                value = value.encode('utf-8')
            decrypted = fernet.decrypt(value)
            return decrypted.decode('utf-8')
        except InvalidToken:
            logger.error("Decryption failed: Invalid token (wrong key or corrupted data)")
            return ""  # Return empty string instead of crashing
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return ""  # Return empty string instead of crashing

except ImportError:
    # Fallback for development if cryptography is not installed
    logger.warning("cryptography module not installed. Using mock encryption (NOT SECURE!)")
    
    def encrypt(value: str) -> str:
        """Mock encryption (returns plaintext)."""
        return value if value else ""
    
    def decrypt(value: str) -> str:
        """Mock decryption (returns plaintext)."""
        return value if value else ""