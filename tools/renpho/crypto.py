"""AES-128-ECB encryption/decryption utilities for Renpho API."""

import base64
import json
from .constants import ENCRYPTION_KEY

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding

    def aes_encrypt(plaintext: str, key: str = ENCRYPTION_KEY) -> str:
        padder = padding.PKCS7(128).padder()
        padded = padder.update(plaintext.encode("utf-8")) + padder.finalize()
        cipher = Cipher(algorithms.AES(key.encode("utf-8")), modes.ECB())
        enc = cipher.encryptor()
        return base64.b64encode(enc.update(padded) + enc.finalize()).decode("utf-8")

    def aes_decrypt(encrypted_b64: str, key: str = ENCRYPTION_KEY) -> str:
        cipher = Cipher(algorithms.AES(key.encode("utf-8")), modes.ECB())
        dec = cipher.decryptor()
        data = dec.update(base64.b64decode(encrypted_b64)) + dec.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        return (unpadder.update(data) + unpadder.finalize()).decode("utf-8")

except ImportError:
    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad, unpad
    except ImportError:
        from Cryptodome.Cipher import AES
        from Cryptodome.Util.Padding import pad, unpad

    def aes_encrypt(plaintext: str, key: str = ENCRYPTION_KEY) -> str:
        cipher = AES.new(key.encode("utf-8"), AES.MODE_ECB)
        padded = pad(plaintext.encode("utf-8"), AES.block_size)
        return base64.b64encode(cipher.encrypt(padded)).decode("utf-8")

    def aes_decrypt(encrypted_b64: str, key: str = ENCRYPTION_KEY) -> str:
        cipher = AES.new(key.encode("utf-8"), AES.MODE_ECB)
        return unpad(cipher.decrypt(base64.b64decode(encrypted_b64)), AES.block_size).decode("utf-8")


def encrypt_request(obj: dict, key: str = ENCRYPTION_KEY) -> dict:
    return {"encryptData": aes_encrypt(json.dumps(obj, separators=(",", ":")), key)}


def encrypt_empty_object(key: str = ENCRYPTION_KEY) -> dict:
    return encrypt_request({}, key)


def encrypt_empty_bytes(key: str = ENCRYPTION_KEY) -> dict:
    return {"encryptData": aes_encrypt("", key)}


def decrypt_response(encrypted_data: str, key: str = ENCRYPTION_KEY):
    return json.loads(aes_decrypt(encrypted_data, key))
