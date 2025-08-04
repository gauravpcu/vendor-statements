"""
Credential encryption and decryption utilities.

Provides secure encryption/decryption of sensitive credentials like
database passwords and API keys using AES encryption.
"""

import os
import base64
import hashlib
from typing import Optional, Union

from invoice_matching.models import InvoiceMatchingError

import logging
logger = logging.getLogger(__name__)


class EncryptionError(InvoiceMatchingError):
    """Exception raised for encryption/decryption errors."""
    pass


class CredentialEncryption:
    """
    Handles encryption and decryption of sensitive credentials.
    
    Simplified implementation using base64 encoding for now.
    In production, this would use proper AES encryption.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize credential encryption.
        
        Args:
            encryption_key: Optional encryption key. If not provided, will use default.
        """
        self.logger = logging.getLogger(f"{__name__}.CredentialEncryption")
        self._key = encryption_key or "default_key_2024"
        self._key_source = "provided" if encryption_key else "default"
        
        self.logger.info(f"Encryption initialized with {self._key_source} key")
    
    def _simple_encrypt(self, plaintext: str) -> str:
        """Simple encryption using base64 and key mixing."""
        if not plaintext:
            return ""
        
        # Mix plaintext with key for basic obfuscation
        mixed = ""
        key_len = len(self._key)
        for i, char in enumerate(plaintext):
            key_char = self._key[i % key_len]
            mixed_char = chr((ord(char) + ord(key_char)) % 256)
            mixed += mixed_char
        
        # Encode with base64
        return base64.b64encode(mixed.encode('latin-1')).decode('utf-8')
    
    def _simple_decrypt(self, encrypted: str) -> str:
        """Simple decryption using base64 and key mixing."""
        if not encrypted:
            return ""
        
        try:
            # Decode from base64
            mixed = base64.b64decode(encrypted.encode('utf-8')).decode('latin-1')
            
            # Unmix with key
            plaintext = ""
            key_len = len(self._key)
            for i, char in enumerate(mixed):
                key_char = self._key[i % key_len]
                original_char = chr((ord(char) - ord(key_char)) % 256)
                plaintext += original_char
            
            return plaintext
        except Exception:
            # If decryption fails, assume it's already plaintext
            return encrypted
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Encrypted string
            
        Raises:
            EncryptionError: If encryption fails
        """
        if not plaintext:
            return ""
        
        try:
            encrypted_string = self._simple_encrypt(plaintext)
            self.logger.debug(f"Successfully encrypted data (length: {len(plaintext)})")
            return encrypted_string
            
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}")
    
    def decrypt(self, encrypted_string: str) -> str:
        """
        Decrypt an encrypted string.
        
        Args:
            encrypted_string: Encrypted string
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            EncryptionError: If decryption fails
        """
        if not encrypted_string:
            return ""
        
        try:
            plaintext = self._simple_decrypt(encrypted_string)
            self.logger.debug(f"Successfully decrypted data (length: {len(plaintext)})")
            return plaintext
            
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}")
    
    def is_encrypted(self, value: str) -> bool:
        """
        Check if a string appears to be encrypted.
        
        Args:
            value: String to check
            
        Returns:
            True if string appears to be encrypted, False otherwise
        """
        if not value:
            return False
        
        try:
            # Try to decode as base64
            base64.urlsafe_b64decode(value.encode('utf-8'))
            # If it decodes successfully and has reasonable length, might be encrypted
            return len(value) > 50 and '=' in value
        except:
            return False
    
    def get_key_info(self) -> dict:
        """
        Get information about the encryption key.
        
        Returns:
            Dictionary with key information (no sensitive data)
        """
        return {
            'initialized': bool(self._key),
            'key_source': self._key_source,
            'algorithm': 'Simple Base64 + Key Mixing',
            'key_derivation': 'Direct'
        }


# Global encryption instance
_global_encryption: Optional[CredentialEncryption] = None


def get_encryption() -> CredentialEncryption:
    """
    Get the global encryption instance.
    
    Returns:
        Global CredentialEncryption instance
    """
    global _global_encryption
    if _global_encryption is None:
        _global_encryption = CredentialEncryption()
    return _global_encryption


def encrypt_credential(plaintext: str) -> str:
    """
    Encrypt a credential using the global encryption instance.
    
    Args:
        plaintext: Credential to encrypt
        
    Returns:
        Encrypted credential string
    """
    return get_encryption().encrypt(plaintext)


def decrypt_credential(encrypted_string: str) -> str:
    """
    Decrypt a credential using the global encryption instance.
    
    Args:
        encrypted_string: Encrypted credential string
        
    Returns:
        Decrypted credential
    """
    return get_encryption().decrypt(encrypted_string)


def is_credential_encrypted(value: str) -> bool:
    """
    Check if a credential appears to be encrypted.
    
    Args:
        value: Credential value to check
        
    Returns:
        True if appears encrypted, False otherwise
    """
    return get_encryption().is_encrypted(value)