from __future__ import annotations

import os
import secrets
import sqlite3
from base64 import urlsafe_b64encode
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidKey
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from eth_account import Account


class WalletStoreError(RuntimeError):
    pass


class InvalidMasterPassword(WalletStoreError):
    pass


class StoreNotUnlocked(WalletStoreError):
    pass


class WalletStore:
    """Encrypted local storage for BSC/EVM deposit wallets."""

    PBKDF2_ITERATIONS = 600_000
    CHECK_VALUE = b"BSC-GUI-MASTER-CHECK-v1"

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._fernet: Fernet | None = None
        self._create_schema()

    def _create_schema(self) -> None:
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value BLOB NOT NULL
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS wallets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL,
                    address TEXT NOT NULL UNIQUE,
                    encrypted_private_key BLOB NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def _get_meta(self, key: str) -> bytes | None:
        row = self.conn.execute(
            "SELECT value FROM meta WHERE key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        return bytes(row["value"])

    def _set_meta(self, key: str, value: bytes) -> None:
        self.conn.execute(
            """
            INSERT INTO meta(key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )

    @classmethod
    def _derive_fernet(cls, password: str, salt: bytes) -> Fernet:
        if not password:
            raise InvalidMasterPassword("La contraseña maestra no puede estar vacía.")

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=cls.PBKDF2_ITERATIONS,
        )
        key = urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
        return Fernet(key)

    def is_initialized(self) -> bool:
        return (
            self._get_meta("salt") is not None
            and self._get_meta("password_check") is not None
        )

    def setup(self, password: str) -> None:
        if self.is_initialized():
            raise WalletStoreError("El almacén ya está inicializado.")
        if len(password) < 10:
            raise WalletStoreError(
                "La contraseña maestra debe tener al menos 10 caracteres."
            )

        salt = os.urandom(16)
        fernet = self._derive_fernet(password, salt)
        password_check = fernet.encrypt(self.CHECK_VALUE)

        with self.conn:
            self._set_meta("salt", salt)
            self._set_meta("password_check", password_check)

        self._fernet = fernet

    def unlock(self, password: str) -> None:
        salt = self._get_meta("salt")
        password_check = self._get_meta("password_check")
        if salt is None or password_check is None:
            raise WalletStoreError("El almacén todavía no fue inicializado.")

        try:
            fernet = self._derive_fernet(password, salt)
            if fernet.decrypt(password_check) != self.CHECK_VALUE:
                raise InvalidMasterPassword("Contraseña maestra incorrecta.")
        except (InvalidToken, InvalidKey, ValueError) as exc:
            raise InvalidMasterPassword("Contraseña maestra incorrecta.") from exc

        self._fernet = fernet

    def _require_unlocked(self) -> Fernet:
        if self._fernet is None:
            raise StoreNotUnlocked("El almacén está bloqueado.")
        return self._fernet

    def create_wallet(self, label: str) -> dict[str, Any]:
        fernet = self._require_unlocked()
        label = label.strip() or "Wallet"

        # Account.create() uses secure OS entropy; extra entropy is supplied as well.
        account = Account.create(extra_entropy=secrets.token_bytes(32))
        private_key = "0x" + bytes(account.key).hex()
        encrypted_key = fernet.encrypt(private_key.encode("ascii"))
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO wallets(label, address, encrypted_private_key, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (label, account.address, encrypted_key, created_at),
            )

        return {
            "id": int(cursor.lastrowid),
            "label": label,
            "address": account.address,
            "created_at": created_at,
        }

    def list_wallets(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT id, label, address, created_at
            FROM wallets
            ORDER BY id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def get_wallet(self, wallet_id: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT id, label, address, created_at
            FROM wallets
            WHERE id = ?
            """,
            (wallet_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    def get_private_key(self, wallet_id: int) -> str:
        fernet = self._require_unlocked()
        row = self.conn.execute(
            "SELECT encrypted_private_key FROM wallets WHERE id = ?",
            (wallet_id,),
        ).fetchone()
        if row is None:
            raise WalletStoreError("Wallet inexistente.")

        try:
            return fernet.decrypt(bytes(row["encrypted_private_key"])).decode("ascii")
        except InvalidToken as exc:
            raise WalletStoreError(
                "No se pudo descifrar la clave privada."
            ) from exc

    def close(self) -> None:
        self._fernet = None
        self.conn.close()
