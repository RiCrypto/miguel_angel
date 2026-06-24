# Security guide

miguel_angel runs entirely on your local machine. No data is ever transmitted to external servers, cloud storage, or any third party. All authentication and encryption happens offline.

## First-run setup

When you launch miguel_angel for the first time, a 5-step setup wizard guides you through:

### Step 1 — Create your profile

Fill in your personal and professional information:

| Field | Required | Notes |
|-------|----------|-------|
| First name | Yes | Minimum 2 characters, no digits |
| Last name | Yes | Minimum 2 characters, no digits |
| Professional email | Yes | RFC 5322 format |
| Organisation | Yes | Minimum 2 characters |
| Role / job title | Yes | Free text |
| Country | Yes | ISO 3166-1 dropdown |
| Recovery email | Optional | Strongly recommended |

### Step 2 — Set your password

Your password must meet these requirements:

- Minimum 12 characters
- At least one uppercase letter
- At least one digit
- At least one special character (`!@#$%^&*` etc.)
- Password strength score ≥ "Fair" (assessed by zxcvbn)

Passwords are hashed using **Argon2id** with the following parameters:

```
time_cost=3, memory_cost=65536 (64 MB), parallelism=4, hash_len=32
```

The profile database is encrypted with **AES-256** (Fernet). The encryption key is derived from your password using **PBKDF2-HMAC-SHA256** with 480,000 iterations and a random 16-byte salt. The salt is stored in plaintext; the key is never stored.

### Step 3 — Validation 1: TOTP

Scan the QR code with any TOTP-compatible authenticator app:

- Google Authenticator
- Authy
- Microsoft Authenticator
- Bitwarden Authenticator
- Any RFC 6238-compliant app

Enter the 6-digit code to verify setup. You will also receive **10 single-use backup codes** — store these securely offline. Each code can only be used once.

TOTP operates completely offline. No internet connection is needed to authenticate.

### Step 4 — Validation 2: Hardware or biometric

Choose your second validation method:

| Method | Security level | Notes |
|--------|---------------|-------|
| FIDO2 USB key (YubiKey, OnlyKey) | Highest | CTAP2, plug in and tap |
| Windows Hello (face / fingerprint) | High | OS credential API |
| Email OTP | Fallback | One-time code to recovery email, no internet needed |

### Step 5 — Complete

Both validations confirmed. miguel_angel unlocks and creates your first session token (valid for 8 hours).

---

## Login flow (every session)

Every time you launch miguel_angel:

1. Enter your password
2. Enter the 6-digit TOTP code from your authenticator app (or a backup code)
3. Present your hardware key or biometric (if enrolled)

After **3 consecutive failed attempts**, the account is locked for **15 minutes**. Use your recovery email OTP to restore access.

---

## Data storage

All user data is stored in the operating system's local application data directory:

| OS | Path |
|----|------|
| Windows | `%LOCALAPPDATA%\miguel_angel\profile.db` |
| macOS | `~/Library/Application Support/miguel_angel/profile.db` |
| Linux | `~/.local/share/miguel_angel/profile.db` |

The `profile.db` file is a SQLite database containing:

- An encrypted blob (AES-256) with all profile fields and the TOTP secret
- The PBKDF2 salt (plaintext — not secret)
- SHA-256 hashed backup codes (one-way hash — originals not stored)
- FIDO2 credential public key (if enrolled)
- Login attempt records and session tokens

**Never commit `profile.db` to version control.** It is listed in `.gitignore`.

---

## Reporting security vulnerabilities

Please do **not** open a public GitHub issue for security vulnerabilities. Instead, use GitHub's private security advisory feature:

1. Go to https://github.com/RiCrypto/miguel_angel/security/advisories
2. Click "Report a vulnerability"
3. Describe the issue in detail

We aim to respond within 48 hours.
