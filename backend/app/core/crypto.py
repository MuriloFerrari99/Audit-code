"""Criptografia simétrica para segredos em repouso (credenciais de ERP por tenant).

Fernet com chave derivada de APP_SECRET_KEY. Em produção, usar KMS/secret manager;
aqui é o mínimo para não guardar credencial de cliente em texto puro.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import get_settings


def _fernet() -> Fernet:
    key = hashlib.sha256(get_settings().app_secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
