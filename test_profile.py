"""
Tests for miguel_angel UserProfile security module.
Run with: pytest tests/test_profile.py -v
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.profile import (
    UserProfile, TOTPEngine, CryptoEngine,
    ProfileValidator, BACKUP_CODE_COUNT
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────

VALID_FORM = {
    "first_name":     "Ricardo",
    "last_name":      "Almeida",
    "email":          "r.almeida@company.com",
    "organisation":   "Acme Engineering Ltd",
    "role":           "Electrical Engineer",
    "country":        "Brazil",
    "password":       "SecureP@ss123!",
    "confirm_password": "SecureP@ss123!",
    "recovery_email": "r.almeida@gmail.com",
}


@pytest.fixture
def tmp_profile(tmp_path):
    """Return a UserProfile instance backed by a temp SQLite DB."""
    return UserProfile(db_path=tmp_path / "profile.db")


# ─── ProfileValidator tests ───────────────────────────────────────────────────

class TestProfileValidator:

    def test_valid_form_passes(self):
        assert ProfileValidator.validate(VALID_FORM) == []

    def test_short_first_name_fails(self):
        data = {**VALID_FORM, "first_name": "A"}
        errors = ProfileValidator.validate(data)
        assert any("First Name" in e for e in errors)

    def test_name_with_digits_fails(self):
        data = {**VALID_FORM, "first_name": "Ricard0"}
        errors = ProfileValidator.validate(data)
        assert any("First Name" in e for e in errors)

    def test_invalid_email_fails(self):
        data = {**VALID_FORM, "email": "not-an-email"}
        errors = ProfileValidator.validate(data)
        assert any("Email" in e for e in errors)

    def test_short_password_fails(self):
        data = {**VALID_FORM, "password": "short", "confirm_password": "short"}
        errors = ProfileValidator.validate(data)
        assert any("Password" in e for e in errors)

    def test_password_no_uppercase_fails(self):
        data = {**VALID_FORM, "password": "securep@ss123!", "confirm_password": "securep@ss123!"}
        errors = ProfileValidator.validate(data)
        assert any("uppercase" in e for e in errors)

    def test_password_no_symbol_fails(self):
        data = {**VALID_FORM, "password": "SecurePass1234", "confirm_password": "SecurePass1234"}
        errors = ProfileValidator.validate(data)
        assert any("special character" in e for e in errors)

    def test_password_mismatch_fails(self):
        data = {**VALID_FORM, "confirm_password": "DifferentPass!1"}
        errors = ProfileValidator.validate(data)
        assert any("do not match" in e for e in errors)

    def test_invalid_recovery_email_fails(self):
        data = {**VALID_FORM, "recovery_email": "bad-email"}
        errors = ProfileValidator.validate(data)
        assert any("Recovery email" in e for e in errors)

    def test_optional_recovery_email_empty_passes(self):
        data = {**VALID_FORM, "recovery_email": ""}
        assert ProfileValidator.validate(data) == []


# ─── CryptoEngine tests ───────────────────────────────────────────────────────

class TestCryptoEngine:

    def test_encrypt_decrypt_roundtrip(self):
        data     = {"name": "Ricardo", "secret": "mysecret42"}
        password = "TestP@ss123!"
        salt     = b"0" * 16
        encrypted = CryptoEngine.encrypt(data, password, salt)
        decrypted = CryptoEngine.decrypt(encrypted, password, salt)
        assert decrypted == data

    def test_wrong_password_raises(self):
        data      = {"name": "test"}
        password  = "CorrectP@ss1!"
        wrong_pw  = "WrongP@ss1234!"
        salt      = b"1" * 16
        encrypted = CryptoEngine.encrypt(data, password, salt)
        with pytest.raises(ValueError, match="Decryption failed"):
            CryptoEngine.decrypt(encrypted, wrong_pw, salt)

    def test_different_salts_produce_different_keys(self):
        password = "TestP@ss123!"
        salt_a   = b"a" * 16
        salt_b   = b"b" * 16
        key_a    = CryptoEngine.derive_key(password, salt_a)
        key_b    = CryptoEngine.derive_key(password, salt_b)
        assert key_a != key_b


# ─── TOTPEngine tests ─────────────────────────────────────────────────────────

class TestTOTPEngine:

    def test_secret_generation_is_unique(self):
        secrets = {TOTPEngine.generate_secret() for _ in range(10)}
        assert len(secrets) == 10

    def test_valid_totp_code_verifies(self):
        import pyotp
        secret = TOTPEngine.generate_secret()
        code   = pyotp.TOTP(secret).now()
        assert TOTPEngine.verify(secret, code) is True

    def test_invalid_totp_code_rejected(self):
        secret = TOTPEngine.generate_secret()
        assert TOTPEngine.verify(secret, "000000") is False

    def test_qr_bytes_returns_png(self):
        secret = TOTPEngine.generate_secret()
        png    = TOTPEngine.generate_qr_bytes(secret, "test@test.com")
        assert png[:8] == b"\x89PNG\r\n\x1a\n"   # PNG magic bytes

    def test_backup_code_count(self):
        codes = TOTPEngine.generate_backup_codes()
        assert len(codes) == BACKUP_CODE_COUNT

    def test_backup_code_verify_match(self):
        code        = TOTPEngine.generate_backup_codes(1)[0]
        code_hash   = TOTPEngine.hash_backup_code(code)
        result      = TOTPEngine.verify_backup_code(code, [code_hash])
        assert result == code_hash

    def test_backup_code_wrong_rejected(self):
        code_hash = TOTPEngine.hash_backup_code("REALCODE12345678")
        result    = TOTPEngine.verify_backup_code("WRONGCODE1234567", [code_hash])
        assert result is None

    def test_backup_codes_are_uppercase_hex(self):
        codes = TOTPEngine.generate_backup_codes()
        for code in codes:
            assert code == code.upper()
            assert len(code) == 16


# ─── UserProfile integration tests ───────────────────────────────────────────

class TestUserProfile:

    def test_profile_not_exists_initially(self, tmp_profile):
        assert tmp_profile.profile_exists() is False

    def test_begin_registration_returns_png(self, tmp_profile):
        png = tmp_profile.begin_registration(VALID_FORM)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"

    def test_begin_registration_invalid_form_raises(self, tmp_profile):
        bad_data = {**VALID_FORM, "email": "not-valid"}
        with pytest.raises(ValueError):
            tmp_profile.begin_registration(bad_data)

    def test_complete_registration_creates_profile(self, tmp_profile):
        import pyotp
        tmp_profile.begin_registration(VALID_FORM)
        totp_code = pyotp.TOTP(tmp_profile._pending_totp_secret).now()
        token = tmp_profile.complete_registration(VALID_FORM, totp_code)
        assert isinstance(token, str) and len(token) == 64
        assert tmp_profile.profile_exists() is True

    def test_complete_registration_wrong_totp_raises(self, tmp_profile):
        tmp_profile.begin_registration(VALID_FORM)
        with pytest.raises(ValueError, match="Invalid TOTP"):
            tmp_profile.complete_registration(VALID_FORM, "000000")

    def test_login_success(self, tmp_profile):
        import pyotp
        tmp_profile.begin_registration(VALID_FORM)
        secret    = tmp_profile._pending_totp_secret
        totp_code = pyotp.TOTP(secret).now()
        tmp_profile.complete_registration(VALID_FORM, totp_code)

        login_code = pyotp.TOTP(secret).now()
        token = tmp_profile.login(
            VALID_FORM["email"],
            VALID_FORM["password"],
            login_code,
        )
        assert tmp_profile.validate_session(token) is True

    def test_login_wrong_password_raises(self, tmp_profile):
        import pyotp
        tmp_profile.begin_registration(VALID_FORM)
        secret    = tmp_profile._pending_totp_secret
        totp_code = pyotp.TOTP(secret).now()
        tmp_profile.complete_registration(VALID_FORM, totp_code)

        with pytest.raises(ValueError, match="Incorrect password"):
            tmp_profile.login(VALID_FORM["email"], "WrongP@ss999!", "123456")

    def test_login_wrong_totp_raises(self, tmp_profile):
        import pyotp
        tmp_profile.begin_registration(VALID_FORM)
        secret    = tmp_profile._pending_totp_secret
        totp_code = pyotp.TOTP(secret).now()
        tmp_profile.complete_registration(VALID_FORM, totp_code)

        with pytest.raises(ValueError, match="Invalid TOTP"):
            tmp_profile.login(
                VALID_FORM["email"],
                VALID_FORM["password"],
                "000000",
            )

    def test_lockout_after_max_attempts(self, tmp_profile):
        import pyotp
        tmp_profile.begin_registration(VALID_FORM)
        secret    = tmp_profile._pending_totp_secret
        totp_code = pyotp.TOTP(secret).now()
        tmp_profile.complete_registration(VALID_FORM, totp_code)

        for _ in range(3):
            try:
                tmp_profile.login(VALID_FORM["email"], "WrongP@ss!", "000000")
            except ValueError:
                pass

        with pytest.raises(ValueError, match="Account locked"):
            tmp_profile.login(
                VALID_FORM["email"],
                VALID_FORM["password"],
                pyotp.TOTP(secret).now(),
            )

    def test_backup_code_login(self, tmp_profile):
        import pyotp
        tmp_profile.begin_registration(VALID_FORM)
        secret    = tmp_profile._pending_totp_secret
        totp_code = pyotp.TOTP(secret).now()
        tmp_profile.complete_registration(VALID_FORM, totp_code)
        backup_code = tmp_profile._last_backup_codes[0]

        token = tmp_profile.login(
            VALID_FORM["email"],
            VALID_FORM["password"],
            totp_code="",
            backup_code=backup_code,
        )
        assert tmp_profile.validate_session(token) is True

    def test_backup_code_consumed_after_use(self, tmp_profile):
        import pyotp
        tmp_profile.begin_registration(VALID_FORM)
        secret    = tmp_profile._pending_totp_secret
        totp_code = pyotp.TOTP(secret).now()
        tmp_profile.complete_registration(VALID_FORM, totp_code)
        backup_code = tmp_profile._last_backup_codes[0]

        # First use — should succeed
        tmp_profile.login(
            VALID_FORM["email"],
            VALID_FORM["password"],
            totp_code="",
            backup_code=backup_code,
        )
        # Second use — should fail (consumed)
        with pytest.raises(ValueError, match="Invalid backup code"):
            tmp_profile.login(
                VALID_FORM["email"],
                VALID_FORM["password"],
                totp_code="",
                backup_code=backup_code,
            )

    def test_complete_registration_without_begin_raises(self, tmp_profile):
        with pytest.raises(RuntimeError, match="begin_registration"):
            tmp_profile.complete_registration(VALID_FORM, "123456")

    def test_session_validation(self, tmp_profile):
        import pyotp
        tmp_profile.begin_registration(VALID_FORM)
        secret    = tmp_profile._pending_totp_secret
        totp_code = pyotp.TOTP(secret).now()
        token = tmp_profile.complete_registration(VALID_FORM, totp_code)
        assert tmp_profile.validate_session(token) is True
        assert tmp_profile.validate_session("invalid-token") is False
