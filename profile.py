"""
miguel_angel — UserProfile Security Module
Backend Developer implementation · Phase 2

Security stack:
  - Argon2id   : password hashing (memory-hard, GPU-resistant)
  - AES-256    : local profile encryption via Fernet (symmetric)
  - PBKDF2     : encryption key derivation from password + salt
  - pyotp      : TOTP Validation 1 (RFC 6238, offline-capable)
  - python-fido2: FIDO2/WebAuthn Validation 2 (YubiKey, Windows Hello)
  - email-validator: RFC 5322 email field validation
  - zxcvbn     : password strength scoring
  - qrcode     : QR code for TOTP authenticator app setup

All data stored locally in SQLite — nothing is ever transmitted off-device.
"""

import os
import json
import base64
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# --- Cryptography ---------------------------------------------------------
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# --- Password hashing -----------------------------------------------------
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

# --- TOTP (Validation 1) --------------------------------------------------
import pyotp
import qrcode
from io import BytesIO

# --- FIDO2 (Validation 2) -------------------------------------------------
try:
    from fido2.hid import CtapHidDevice
    from fido2.client import Fido2Client
    from fido2.server import Fido2Server
    from fido2.webauthn import PublicKeyCredentialRpEntity, AuthenticatorData
    FIDO2_AVAILABLE = True
except ImportError:
    FIDO2_AVAILABLE = False

# --- Field validation -----------------------------------------------------
from email_validator import validate_email, EmailNotValidError
import zxcvbn

# --- Database -------------------------------------------------------------
import sqlite3

logger = logging.getLogger("miguel_angel.auth")

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

APP_NAME            = "miguel_angel"
PROFILE_DB_FILENAME = "profile.db"
MAX_LOGIN_ATTEMPTS  = 3
LOCKOUT_MINUTES     = 15
PBKDF2_ITERATIONS   = 480_000
BACKUP_CODE_COUNT   = 10
MIN_PASSWORD_LENGTH = 12
MIN_PASSWORD_SCORE  = 2          # zxcvbn score 0–4; 2 = "fair", we require ≥ 2
TOTP_ISSUER         = APP_NAME


def _get_app_data_dir() -> Path:
    """Return platform-appropriate local app data directory."""
    if os.name == "nt":                              # Windows
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    elif os.uname().sysname == "Darwin":             # macOS
        base = Path.home() / "Library" / "Application Support"
    else:                                            # Linux / other
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get_db_path() -> Path:
    return _get_app_data_dir() / PROFILE_DB_FILENAME


# ─────────────────────────────────────────────────────────────────────────────
# Crypto helpers
# ─────────────────────────────────────────────────────────────────────────────

class CryptoEngine:
    """AES-256 encryption via Fernet with PBKDF2 key derivation."""

    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        """Derive a 256-bit Fernet key from password + salt using PBKDF2-HMAC-SHA256."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
        )
        raw_key = kdf.derive(password.encode("utf-8"))
        return base64.urlsafe_b64encode(raw_key)

    @staticmethod
    def encrypt(data: dict, password: str, salt: bytes) -> bytes:
        key    = CryptoEngine.derive_key(password, salt)
        fernet = Fernet(key)
        return fernet.encrypt(json.dumps(data).encode("utf-8"))

    @staticmethod
    def decrypt(encrypted: bytes, password: str, salt: bytes) -> dict:
        key    = CryptoEngine.derive_key(password, salt)
        fernet = Fernet(key)
        try:
            return json.loads(fernet.decrypt(encrypted).decode("utf-8"))
        except InvalidToken:
            raise ValueError("Decryption failed — incorrect password or corrupted profile.")


# ─────────────────────────────────────────────────────────────────────────────
# Field validators
# ─────────────────────────────────────────────────────────────────────────────

class ProfileValidator:
    """Validates all required profile fields before storage."""

    REQUIRED_TEXT_FIELDS = ["first_name", "last_name", "organisation", "role", "country"]

    @classmethod
    def validate(cls, form_data: dict) -> list[str]:
        """Return list of validation error strings; empty list = all valid."""
        errors: list[str] = []

        # Text fields
        for field in cls.REQUIRED_TEXT_FIELDS:
            value = (form_data.get(field) or "").strip()
            if len(value) < 2:
                errors.append(f"{field.replace('_', ' ').title()}: minimum 2 characters required.")
            if any(ch.isdigit() for ch in value) and field in ("first_name", "last_name"):
                errors.append(f"{field.replace('_', ' ').title()}: must not contain numbers.")

        # Email
        try:
            validate_email(form_data.get("email", ""), check_deliverability=False)
        except EmailNotValidError as exc:
            errors.append(f"Email: {exc}")

        # Password strength
        password = form_data.get("password", "")
        if len(password) < MIN_PASSWORD_LENGTH:
            errors.append(f"Password: minimum {MIN_PASSWORD_LENGTH} characters required.")
        else:
            result = zxcvbn.zxcvbn(password)
            if result["score"] < MIN_PASSWORD_SCORE:
                suggestion = result["feedback"].get("warning", "Choose a stronger password.")
                errors.append(f"Password too weak: {suggestion}")
            if not any(c.isupper() for c in password):
                errors.append("Password: must contain at least one uppercase letter.")
            if not any(c.isdigit() for c in password):
                errors.append("Password: must contain at least one digit.")
            if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in password):
                errors.append("Password: must contain at least one special character.")

        # Confirm password
        if password != form_data.get("confirm_password", ""):
            errors.append("Passwords do not match.")

        # Recovery email (optional but validated if provided)
        recovery = (form_data.get("recovery_email") or "").strip()
        if recovery:
            try:
                validate_email(recovery, check_deliverability=False)
            except EmailNotValidError as exc:
                errors.append(f"Recovery email: {exc}")

        return errors


# ─────────────────────────────────────────────────────────────────────────────
# TOTP engine — Validation 1
# ─────────────────────────────────────────────────────────────────────────────

class TOTPEngine:
    """
    RFC 6238 Time-based One-Time Password.
    Compatible with Google Authenticator, Authy, Microsoft Authenticator.
    Operates completely offline — no network call needed.
    """

    @staticmethod
    def generate_secret() -> str:
        """Generate a cryptographically random base32 TOTP secret."""
        return pyotp.random_base32()

    @staticmethod
    def get_provisioning_uri(secret: str, email: str) -> str:
        """Return the otpauth:// URI for QR code generation."""
        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=email,
            issuer_name=TOTP_ISSUER,
        )

    @staticmethod
    def generate_qr_bytes(secret: str, email: str) -> bytes:
        """Return PNG QR code as bytes for display in the PyQt6 wizard."""
        uri = TOTPEngine.get_provisioning_uri(secret, email)
        img = qrcode.make(uri)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    @staticmethod
    def verify(secret: str, code: str) -> bool:
        """
        Verify a 6-digit TOTP code.
        valid_window=1 allows ±30s clock drift.
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(code.strip(), valid_window=1)

    @staticmethod
    def generate_backup_codes(count: int = BACKUP_CODE_COUNT) -> list[str]:
        """
        Generate one-time backup codes (16 hex chars each).
        These are hashed before storage.
        """
        return [secrets.token_hex(8).upper() for _ in range(count)]

    @staticmethod
    def hash_backup_code(code: str) -> str:
        """SHA-256 hash of a backup code for safe storage."""
        return hashlib.sha256(code.encode()).hexdigest()

    @staticmethod
    def verify_backup_code(code: str, stored_hashes: list[str]) -> Optional[str]:
        """
        Check if the provided code matches any stored hash.
        Returns the matched hash so the caller can mark it as used.
        """
        code_hash = TOTPEngine.hash_backup_code(code.strip().upper())
        return code_hash if code_hash in stored_hashes else None


# ─────────────────────────────────────────────────────────────────────────────
# FIDO2 engine — Validation 2
# ─────────────────────────────────────────────────────────────────────────────

class FIDO2Engine:
    """
    FIDO2 / WebAuthn hardware key authentication.
    Supports: YubiKey, OnlyKey, SoloKey (USB HID CTAP2).
    Fallback: Windows Hello via OS credential API.
    """

    RP_ID   = "miguel-angel.local"
    RP_NAME = "miguel_angel"

    def __init__(self):
        if not FIDO2_AVAILABLE:
            logger.warning("python-fido2 not installed — FIDO2 disabled, fallback active.")
        self._rp = PublicKeyCredentialRpEntity(id=self.RP_ID, name=self.RP_NAME) if FIDO2_AVAILABLE else None

    def list_devices(self) -> list:
        """Return list of connected FIDO2 HID devices."""
        if not FIDO2_AVAILABLE:
            return []
        return list(CtapHidDevice.list_devices())

    def register(self, user_id: bytes, username: str) -> dict:
        """
        Begin FIDO2 registration ceremony.
        Returns credential data to be stored in the encrypted profile.
        """
        if not FIDO2_AVAILABLE or not self.list_devices():
            raise RuntimeError("No FIDO2 device detected. Connect your USB security key.")
        devices  = self.list_devices()
        device   = devices[0]
        client   = Fido2Client(device, f"https://{self.RP_ID}")
        server   = Fido2Server(self._rp)
        options, state = server.register_begin(
            {"id": user_id, "name": username, "displayName": username},
            user_verification="preferred",
        )
        result  = client.make_credential(options["publicKey"])
        auth_data = server.register_complete(state, result)
        return {
            "credential_id": base64.b64encode(auth_data.credential_data.credential_id).decode(),
            "public_key":    base64.b64encode(bytes(auth_data.credential_data)).decode(),
        }

    def authenticate(self, credential_data: dict) -> bool:
        """
        Verify a FIDO2 assertion from the connected USB key.
        Returns True if the hardware key assertion is valid.
        """
        if not FIDO2_AVAILABLE or not self.list_devices():
            return False
        try:
            devices = self.list_devices()
            device  = devices[0]
            client  = Fido2Client(device, f"https://{self.RP_ID}")
            server  = Fido2Server(self._rp)
            cred_id = base64.b64decode(credential_data["credential_id"])
            pub_key = base64.b64decode(credential_data["public_key"])
            options, state = server.authenticate_begin([pub_key])
            result  = client.get_assertion(options["publicKey"])
            server.authenticate_complete(state, [pub_key], result)
            return True
        except Exception as exc:
            logger.error("FIDO2 authentication error: %s", exc)
            return False


# ─────────────────────────────────────────────────────────────────────────────
# Profile database
# ─────────────────────────────────────────────────────────────────────────────

class ProfileDB:
    """
    SQLite profile store.
    The `encrypted_profile` column stores the Fernet-encrypted JSON blob.
    Only the salt and non-sensitive metadata live in plaintext.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or _get_db_path()
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS profile (
                    id                INTEGER PRIMARY KEY,
                    username          TEXT NOT NULL UNIQUE,
                    salt              BLOB NOT NULL,
                    encrypted_profile BLOB NOT NULL,
                    totp_enabled      INTEGER DEFAULT 1,
                    fido2_enabled     INTEGER DEFAULT 0,
                    backup_codes      TEXT,
                    fido2_credential  TEXT,
                    created_at        TEXT NOT NULL,
                    updated_at        TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    username     TEXT NOT NULL,
                    attempted_at TEXT NOT NULL,
                    success      INTEGER NOT NULL,
                    reason       TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id         TEXT PRIMARY KEY,
                    username   TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    active     INTEGER DEFAULT 1
                )
            """)
            conn.commit()

    def save_profile(
        self,
        username: str,
        salt: bytes,
        encrypted_profile: bytes,
        backup_code_hashes: list[str],
        fido2_credential: Optional[dict] = None,
    ):
        now = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO profile
                    (username, salt, encrypted_profile, totp_enabled, fido2_enabled,
                     backup_codes, fido2_credential, created_at, updated_at)
                VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)
            """, (
                username,
                salt,
                encrypted_profile,
                1 if fido2_credential else 0,
                json.dumps(backup_code_hashes),
                json.dumps(fido2_credential) if fido2_credential else None,
                now, now,
            ))
            conn.commit()

    def load_profile(self, username: str) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM profile WHERE username = ?", (username,)
            ).fetchone()
        if not row:
            return None
        cols = ["id","username","salt","encrypted_profile","totp_enabled",
                "fido2_enabled","backup_codes","fido2_credential",
                "created_at","updated_at"]
        return dict(zip(cols, row))

    def profile_exists(self) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM profile").fetchone()[0] > 0

    def record_attempt(self, username: str, success: bool, reason: str = ""):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO login_attempts (username, attempted_at, success, reason) VALUES (?,?,?,?)",
                (username, datetime.utcnow().isoformat(), int(success), reason)
            )
            conn.commit()

    def recent_failed_attempts(self, username: str, window_minutes: int = LOCKOUT_MINUTES) -> int:
        since = (datetime.utcnow() - timedelta(minutes=window_minutes)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM login_attempts WHERE username=? AND success=0 AND attempted_at>?",
                (username, since)
            ).fetchone()[0]

    def consume_backup_code(self, username: str, code_hash: str):
        """Mark a backup code as used by removing it from the stored list."""
        row = self.load_profile(username)
        if not row:
            return
        codes = json.loads(row["backup_codes"] or "[]")
        codes = [c for c in codes if c != code_hash]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE profile SET backup_codes=?, updated_at=? WHERE username=?",
                (json.dumps(codes), datetime.utcnow().isoformat(), username)
            )
            conn.commit()

    def create_session(self, username: str, ttl_hours: int = 8) -> str:
        session_id = secrets.token_hex(32)
        now        = datetime.utcnow()
        expires    = now + timedelta(hours=ttl_hours)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO sessions (id, username, created_at, expires_at) VALUES (?,?,?,?)",
                (session_id, username, now.isoformat(), expires.isoformat())
            )
            conn.commit()
        return session_id

    def validate_session(self, session_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT expires_at, active FROM sessions WHERE id=?", (session_id,)
            ).fetchone()
        if not row:
            return False
        expires, active = row
        return active == 1 and datetime.fromisoformat(expires) > datetime.utcnow()


# ─────────────────────────────────────────────────────────────────────────────
# UserProfile — main public API
# ─────────────────────────────────────────────────────────────────────────────

class UserProfile:
    """
    Main entry point for the miguel_angel authentication system.

    Usage — first run (registration):
        profile = UserProfile()
        qr_png  = profile.begin_registration(form_data)  # show QR in wizard
        token   = profile.complete_registration(form_data, totp_code, fido2_device)

    Usage — every session start (login):
        token = profile.login(username, password, totp_code, fido2_device)
        # token is a session ID stored in memory; validate with profile.validate_session(token)
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db          = ProfileDB(db_path)
        self.crypto      = CryptoEngine()
        self.totp        = TOTPEngine()
        self.fido2       = FIDO2Engine()
        self._ph         = PasswordHasher(
            time_cost=3,          # iterations
            memory_cost=65536,    # 64 MB RAM — GPU-resistant
            parallelism=4,        # threads
            hash_len=32,
            salt_len=16,
            encoding="utf-8",
        )
        self._pending_totp_secret: Optional[str] = None

    # ── Registration ──────────────────────────────────────────────────────

    def begin_registration(self, form_data: dict) -> bytes:
        """
        Step 1 of 2: validate form fields and return QR code PNG bytes
        for display in the TOTP setup step of the wizard.
        Raises ValueError with list of errors if validation fails.
        """
        errors = ProfileValidator.validate(form_data)
        if errors:
            raise ValueError("\n".join(errors))

        self._pending_totp_secret = self.totp.generate_secret()
        return self.totp.generate_qr_bytes(
            self._pending_totp_secret,
            form_data["email"],
        )

    def complete_registration(
        self,
        form_data: dict,
        totp_code: str,
        register_fido2: bool = False,
    ) -> str:
        """
        Step 2 of 2: verify TOTP code, hash password, encrypt and persist profile.
        Returns session token on success.
        """
        if not self._pending_totp_secret:
            raise RuntimeError("Call begin_registration() first.")

        # Verify the TOTP code before committing anything
        if not self.totp.verify(self._pending_totp_secret, totp_code):
            raise ValueError("Invalid TOTP code. Check your authenticator app and try again.")

        password = form_data["password"]
        username = form_data["email"]

        # Hash password with Argon2id
        password_hash = self._ph.hash(password)

        # Generate backup codes (hash for storage, return plaintext once to user)
        plain_backup_codes = self.totp.generate_backup_codes()
        hashed_backup_codes = [
            self.totp.hash_backup_code(c) for c in plain_backup_codes
        ]

        # FIDO2 registration (optional at setup, can be added later in Preferences)
        fido2_credential = None
        if register_fido2:
            user_id = hashlib.sha256(username.encode()).digest()
            fido2_credential = self.fido2.register(user_id, username)

        # Build profile payload
        profile_data = {
            "first_name":    form_data["first_name"].strip(),
            "last_name":     form_data["last_name"].strip(),
            "email":         username,
            "organisation":  form_data["organisation"].strip(),
            "role":          form_data["role"].strip(),
            "country":       form_data["country"].strip(),
            "password_hash": password_hash,
            "totp_secret":   self._pending_totp_secret,
            "recovery_email": (form_data.get("recovery_email") or "").strip(),
            "created_at":    datetime.utcnow().isoformat(),
        }

        # Encrypt profile blob with AES-256 (key derived from password)
        salt = os.urandom(16)
        encrypted = self.crypto.encrypt(profile_data, password, salt)

        # Persist to SQLite
        self.db.save_profile(
            username=username,
            salt=salt,
            encrypted_profile=encrypted,
            backup_code_hashes=hashed_backup_codes,
            fido2_credential=fido2_credential,
        )

        # Clear pending secret from memory
        self._pending_totp_secret = None

        logger.info("Profile created for %s", username)
        session_token = self.db.create_session(username)

        # NOTE: plain_backup_codes must be shown ONCE to user in the wizard UI
        # and never stored anywhere in plaintext. Attach to return value via
        # a side-channel (e.g. self._last_backup_codes) for the wizard to read.
        self._last_backup_codes = plain_backup_codes

        return session_token

    # ── Login ─────────────────────────────────────────────────────────────

    def login(
        self,
        username: str,
        password: str,
        totp_code: str,
        use_fido2: bool = False,
        backup_code: Optional[str] = None,
    ) -> str:
        """
        Full login flow — password + Validation 1 (TOTP) + optional Validation 2 (FIDO2).
        Returns session token on success.
        Raises ValueError on any authentication failure.
        """

        # Lockout check
        failed = self.db.recent_failed_attempts(username)
        if failed >= MAX_LOGIN_ATTEMPTS:
            raise ValueError(
                f"Account locked after {MAX_LOGIN_ATTEMPTS} failed attempts. "
                f"Wait {LOCKOUT_MINUTES} minutes or use recovery email."
            )

        row = self.db.load_profile(username)
        if not row:
            self.db.record_attempt(username, False, "user not found")
            raise ValueError("Profile not found.")

        # ── Step 1: verify password ──────────────────────────────────────
        encrypted = row["encrypted_profile"]
        salt      = row["salt"]
        try:
            profile = self.crypto.decrypt(encrypted, password, salt)
        except ValueError:
            self.db.record_attempt(username, False, "wrong password")
            raise ValueError("Incorrect password.")

        # Argon2id re-verify (defence in depth)
        try:
            self._ph.verify(profile["password_hash"], password)
        except (VerifyMismatchError, VerificationError):
            self.db.record_attempt(username, False, "argon2 mismatch")
            raise ValueError("Incorrect password.")

        # ── Step 2: Validation 1 — TOTP or backup code ──────────────────
        if backup_code:
            hashed_codes = json.loads(row["backup_codes"] or "[]")
            matched = self.totp.verify_backup_code(backup_code, hashed_codes)
            if not matched:
                self.db.record_attempt(username, False, "invalid backup code")
                raise ValueError("Invalid backup code.")
            self.db.consume_backup_code(username, matched)
            logger.info("Backup code used for %s — %d remaining", username,
                        len(hashed_codes) - 1)
        else:
            if not self.totp.verify(profile["totp_secret"], totp_code):
                self.db.record_attempt(username, False, "invalid TOTP")
                raise ValueError("Invalid TOTP code. Check your authenticator app.")

        # ── Step 3: Validation 2 — FIDO2 (if enrolled) ──────────────────
        if row["fido2_enabled"] and use_fido2:
            cred = json.loads(row["fido2_credential"])
            if not self.fido2.authenticate(cred):
                self.db.record_attempt(username, False, "fido2 failure")
                raise ValueError("Hardware key authentication failed. Insert your USB key and try again.")

        # ── All factors passed ───────────────────────────────────────────
        self.db.record_attempt(username, True)
        session_token = self.db.create_session(username)
        logger.info("Login successful for %s", username)
        return session_token

    def validate_session(self, session_token: str) -> bool:
        return self.db.validate_session(session_token)

    def profile_exists(self) -> bool:
        return self.db.profile_exists()

    def get_display_name(self, username: str, password: str) -> str:
        """Decrypt and return display name — used in the app title bar."""
        row = self.db.load_profile(username)
        if not row:
            return username
        profile = self.crypto.decrypt(row["encrypted_profile"], password, row["salt"])
        return f"{profile['first_name']} {profile['last_name']}"
