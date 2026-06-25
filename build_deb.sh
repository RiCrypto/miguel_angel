#!/usr/bin/env bash
# packaging/scripts/build_deb.sh
# Cloud Specialist implementation · Phase 4
#
# Creates a .deb package from the PyInstaller output.
# Must be run after:  pyinstaller packaging/miguel_angel.spec
#
# Usage:
#   bash packaging/scripts/build_deb.sh 0.1.0
#
# Output: dist/miguel_angel_0.1.0_amd64.deb

set -euo pipefail

VERSION="${1:-0.1.0}"
ARCH="amd64"
PACKAGE="miguel-angel"
DEB_NAME="${PACKAGE}_${VERSION}_${ARCH}"
DIST_DIR="dist/miguel_angel"
DEB_ROOT="dist/deb_staging/${DEB_NAME}"

echo "── Building .deb  ${DEB_NAME} ──────────────────────────────────────────"

# ── Verify PyInstaller output exists ─────────────────────────────────────────
if [[ ! -d "${DIST_DIR}" ]]; then
  echo "ERROR: ${DIST_DIR} not found. Run PyInstaller first."
  echo "  pyinstaller packaging/miguel_angel.spec"
  exit 1
fi

# ── Debian package directory structure ───────────────────────────────────────
rm -rf "${DEB_ROOT}"
mkdir -p "${DEB_ROOT}/DEBIAN"
mkdir -p "${DEB_ROOT}/usr/bin"
mkdir -p "${DEB_ROOT}/usr/share/applications"
mkdir -p "${DEB_ROOT}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${DEB_ROOT}/usr/share/miguel-angel"
mkdir -p "${DEB_ROOT}/usr/share/doc/miguel-angel"
mkdir -p "${DEB_ROOT}/usr/share/mime/packages"

# ── Copy application bundle ───────────────────────────────────────────────────
cp -r "${DIST_DIR}/." "${DEB_ROOT}/usr/share/miguel-angel/"
chmod +x "${DEB_ROOT}/usr/share/miguel-angel/miguel_angel"

# ── Create launcher symlink in /usr/bin ───────────────────────────────────────
cat > "${DEB_ROOT}/usr/bin/miguel-angel" << 'LAUNCHER'
#!/bin/bash
exec /usr/share/miguel-angel/miguel_angel "$@"
LAUNCHER
chmod +x "${DEB_ROOT}/usr/bin/miguel-angel"

# ── Desktop entry ─────────────────────────────────────────────────────────────
cat > "${DEB_ROOT}/usr/share/applications/miguel-angel.desktop" << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=miguel_angel
GenericName=Schematic Editor
Comment=Open-source electrical and electronic schematic editor
Exec=/usr/share/miguel-angel/miguel_angel %F
Icon=miguel-angel
Terminal=false
Categories=Engineering;Electronics;Science;
MimeType=application/x-maproj;
Keywords=schematic;electrical;ISA;IEC;ANSI;IED;PLC;SCADA;HMI;
StartupWMClass=miguel_angel
DESKTOP

# ── MIME type registration ─────────────────────────────────────────────────────
cat > "${DEB_ROOT}/usr/share/mime/packages/miguel-angel.xml" << MIME
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-maproj">
    <comment>miguel_angel schematic project</comment>
    <glob pattern="*.maproj"/>
    <magic priority="50">
      <match type="string" offset="0" value='{"version"'/>
    </magic>
  </mime-type>
</mime-info>
MIME

# ── Icon ──────────────────────────────────────────────────────────────────────
if [[ -f "packaging/icons/miguel_angel.png" ]]; then
  cp "packaging/icons/miguel_angel.png" \
     "${DEB_ROOT}/usr/share/icons/hicolor/256x256/apps/miguel-angel.png"
fi

# ── Documentation ─────────────────────────────────────────────────────────────
cp README.md  "${DEB_ROOT}/usr/share/doc/miguel-angel/" 2>/dev/null || true
cp CHANGELOG.md "${DEB_ROOT}/usr/share/doc/miguel-angel/" 2>/dev/null || true
cp LICENSE    "${DEB_ROOT}/usr/share/doc/miguel-angel/" 2>/dev/null || true

gzip -9 -c CHANGELOG.md > \
  "${DEB_ROOT}/usr/share/doc/miguel-angel/changelog.Debian.gz" 2>/dev/null || true

# ── DEBIAN control ────────────────────────────────────────────────────────────
INSTALLED_SIZE=$(du -sk "${DEB_ROOT}/usr" | awk '{print $1}')

cat > "${DEB_ROOT}/DEBIAN/control" << CONTROL
Package: miguel-angel
Version: ${VERSION}
Architecture: ${ARCH}
Maintainer: Ricardo Almeida <ricrypto@github.com>
Installed-Size: ${INSTALLED_SIZE}
Depends: libxcb-cursor0 | libxcb-cursor-dev
Recommends: ollama
Section: electronics
Priority: optional
Homepage: https://github.com/RiCrypto/miguel_angel
Description: Open-source electrical and electronic schematic editor
 miguel_angel is a cross-platform schematic editor supporting ISA 5.1,
 ISA 5.2, ISA 5.4, ISA 95, IEC 60617, ANSI/NEMA, and IEEE 315 standards.
 .
 Features: component library (40 symbols), netlist engine with ERC,
 MiguelBot AI assistant (offline RAG), and export to DXF/PDF/SVG/KiCad.
CONTROL

# ── DEBIAN postinst / prerm ───────────────────────────────────────────────────
cat > "${DEB_ROOT}/DEBIAN/postinst" << 'POSTINST'
#!/bin/sh
set -e
# Update MIME and desktop databases
if command -v update-mime-database >/dev/null 2>&1; then
  update-mime-database /usr/share/mime || true
fi
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache /usr/share/icons/hicolor || true
fi
exit 0
POSTINST
chmod 755 "${DEB_ROOT}/DEBIAN/postinst"

cat > "${DEB_ROOT}/DEBIAN/prerm" << 'PRERM'
#!/bin/sh
set -e
exit 0
PRERM
chmod 755 "${DEB_ROOT}/DEBIAN/prerm"

# ── Build the .deb ────────────────────────────────────────────────────────────
mkdir -p dist
dpkg-deb --build --root-owner-group "${DEB_ROOT}" "dist/${DEB_NAME}.deb"

echo ""
echo "✅  .deb built: dist/${DEB_NAME}.deb"
echo "    Install:  sudo dpkg -i dist/${DEB_NAME}.deb"
echo "    Remove:   sudo dpkg -r miguel-angel"
