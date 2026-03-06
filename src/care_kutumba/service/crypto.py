"""Cryptographic utilities for Kutumba API integration.

This module provides HMAC-SHA256 generation for request authentication
and AES-256-CBC decryption for encrypted response data.
"""

import base64
import hashlib
import hmac
import json
import logging

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

logger = logging.getLogger(__name__)


def generate_hmac(client_code: str, rc_number: str, hmac_key: str) -> str:
    """
    Generate HMAC-SHA256 hash for Kutumba API authentication.

    The message format is: {client_code}__{rc_number}__
    (note the trailing double underscores)

    Args:
        client_code: The client code provided by Kutumba
        rc_number: The ration card number to lookup
        hmac_key: The HMAC secret key

    Returns:
        Base64-encoded HMAC-SHA256 digest
    """
    message = f"{client_code}__{rc_number}__"
    logger.debug("Generating HMAC for message pattern")

    digest = hmac.new(
        hmac_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    hashed_mac = base64.b64encode(digest).decode("utf-8")
    logger.debug("HMAC generated successfully")
    return hashed_mac


def decrypt_response(encrypted_data: str, aes_key: str, aes_iv: str) -> dict:
    """
    Decrypt AES-256-CBC encrypted response from Kutumba API.

    Args:
        encrypted_data: Base64-encoded encrypted data (EncResultData)
        aes_key: AES-256 key as UTF-8 string (32 bytes)
        aes_iv: AES IV as UTF-8 string (16 bytes)

    Returns:
        Decrypted and parsed JSON data

    Raises:
        ValueError: If decryption or JSON parsing fails
    """
    try:
        # Remove any whitespace from base64 data
        b64_data = encrypted_data.replace(" ", "").replace("\n", "")
        ciphertext = base64.b64decode(b64_data)

        # Convert key and IV to bytes (UTF-8 encoding as per the JS implementation)
        key = aes_key.encode("utf-8")
        iv = aes_iv.encode("utf-8")

        # Validate key and IV lengths
        if len(key) != 32:
            raise ValueError(f"AES key must be 32 bytes, got {len(key)}")
        if len(iv) != 16:
            raise ValueError(f"AES IV must be 16 bytes, got {len(iv)}")

        # Create AES-256-CBC cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()

        # Decrypt
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        # Remove PKCS7 padding
        unpadder = PKCS7(algorithms.AES.block_size).unpadder()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

        # Decode and parse JSON
        plaintext_str = plaintext.decode("utf-8")
        logger.debug("Successfully decrypted response data")

        return json.loads(plaintext_str)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse decrypted data as JSON: {e}")
        raise ValueError("Decrypted data is not valid JSON") from e
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise ValueError(f"Failed to decrypt response: {e}") from e
