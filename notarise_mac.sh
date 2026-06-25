#!/usr/bin/env bash
# packaging/scripts/notarise_mac.sh
# Cloud Specialist implementation · Phase 4
#
# Signs and notarises the macOS .app bundle for Gatekeeper.
# Requires: Xcode CLI tools, an Apple Developer account, and
#           the following environment variables set in GitHub Secrets:
#   APPLE_SIGNING_IDENTITY    — "Developer ID Application: Name (TEAMID)"
#   APPLE_ID                  — your Apple ID email
#   APPLE_APP_PASSWORD        — app-specific password (appleid.apple.com)
#   APPLE_TEAM_ID             — 10-character Team ID
#
# Usage (after PyInstaller build):
#   bash packaging/scripts/notarise_mac.sh 0.1.0

set -euo pipefail

VERSION="${1:-0.1.0}"
APP_PATH="dist/miguel_angel.app"
ZIP_PATH="dist/miguel_angel_${VERSION}_mac.zip"

echo "── macOS notarisation for ${APP_PATH} ──────────────────────────────────"

# ── Verify environment ────────────────────────────────────────────────────────
for var in APPLE_SIGNING_IDENTITY APPLE_ID APPLE_APP_PASSWORD APPLE_TEAM_ID; do
  if [[ -z "${!var:-}" ]]; then
    echo "WARNING: ${var} not set — skipping notarisation (unsigned build)"
    echo "The app will show a Gatekeeper warning on first launch."
    exit 0
  fi
done

# ── Sign the .app bundle ──────────────────────────────────────────────────────
echo "Signing..."
codesign \
  --force \
  --options runtime \
  --deep \
  --sign "${APPLE_SIGNING_IDENTITY}" \
  --entitlements "packaging/scripts/entitlements.plist" \
  "${APP_PATH}"

echo "Verifying signature..."
codesign --verify --verbose=2 "${APP_PATH}"
spctl --assess --type exec --verbose "${APP_PATH}"

# ── Zip for notarisation submission ──────────────────────────────────────────
echo "Creating zip for notarisation..."
ditto -c -k --keepParent "${APP_PATH}" "${ZIP_PATH}"

# ── Submit to Apple notarisation service ─────────────────────────────────────
echo "Submitting to notarisation service..."
xcrun notarytool submit "${ZIP_PATH}" \
  --apple-id "${APPLE_ID}" \
  --password "${APPLE_APP_PASSWORD}" \
  --team-id "${APPLE_TEAM_ID}" \
  --wait \
  --timeout 20m

# ── Staple the notarisation ticket ───────────────────────────────────────────
echo "Stapling notarisation ticket..."
xcrun stapler staple "${APP_PATH}"
xcrun stapler validate "${APP_PATH}"

echo ""
echo "✅  Notarisation complete: ${APP_PATH}"
