import base64
import logging
import os
import re
import subprocess
import sys

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15


def extract_and_sign_app_signature(keystore_path: str, keystore_pass: str):
    app_signature_thumbprint = _extract_thumbprint_from_keystore(keystore_path, "key0", keystore_pass, keystore_pass)
    private_key_path = os.path.join(os.getcwd(), "worker", "private_key.pem")
    if not os.path.exists(private_key_path):
        logging.error("private_key.pem DOES NOT EXIST!")
        sys.exit(1)
    with open(private_key_path, "rb") as f:
        private_key_data = f.read()
        return _sign_app_signature(app_signature_thumbprint, private_key_data)


def _extract_thumbprint_from_keystore(keystore_path: str, key_alias: str, store_pass: str, key_pass: str) -> str:
    result = subprocess.run(
        [
            "keytool", "-list", "-v",
            "-keystore", keystore_path,
            "-alias", key_alias,
            "-storepass", store_pass,
            "-keypass", key_pass,
        ],
        capture_output=True,
        encoding="utf-8")
    match = re.search(r'''SHA256: ((?:[\dABCDEF]{2}:){31}[\dABCDEF]{2})''', result.stdout) # SHA256: A1:B2:C3:D4...
    if match is None:
        raise RuntimeError(f"Failed to read SHA256 thumbprint from keystore (keytool exit {result.returncode})")
    return match[1].replace(':', '')


def _sign_app_signature(app_signature: str, private_key_data: bytes) -> str:
    app_signature_bytes = bytes(app_signature, "UTF-8")
    key = RSA.import_key(private_key_data)
    app_signature_hash = SHA256.new(app_signature_bytes)
    signature = pkcs1_15.new(key).sign(app_signature_hash)
    return base64.b64encode(signature).decode("UTF-8")
