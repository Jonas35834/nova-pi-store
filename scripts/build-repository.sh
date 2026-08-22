#!/bin/bash

set -e

VERSION="${1:-1.1.1}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

REPO="$ROOT/apt-repository"

DEB="$ROOT/nova-pi-store_${VERSION}_all.deb"


echo
echo "======================================"
echo "Nova Pi Store APT Repository"
echo "======================================"
echo
echo "Version: $VERSION"
echo


# ============================================================
# Repository löschen
# ============================================================

echo "[1/8] Lösche altes Repository..."

rm -rf "$REPO"


# ============================================================
# Verzeichnisstruktur
# ============================================================

echo "[2/8] Erstelle Repository-Struktur..."

mkdir -p \
    "$REPO/pool/main" \
    "$REPO/dists/stable/main/binary-all"


# ============================================================
# Debian-Paket prüfen
# ============================================================

echo "[3/8] Prüfe Debian-Paket..."

if [ ! -f "$DEB" ]; then

    echo
    echo "FEHLER:"
    echo "Debian-Paket nicht gefunden:"
    echo "$DEB"
    echo

    exit 1

fi


echo
echo "Paket:"
echo "$DEB"
echo


# ============================================================
# Debian-Paket kopieren
# ============================================================

cp \
    "$DEB" \
    "$REPO/pool/main/"


# ============================================================
# Paketinformationen
# ============================================================

echo "[4/8] Lese Paketinformationen..."


PACKAGE_NAME=$(
    dpkg-deb -f "$DEB" Package
)

PACKAGE_VERSION=$(
    dpkg-deb -f "$DEB" Version
)

PACKAGE_ARCHITECTURE=$(
    dpkg-deb -f "$DEB" Architecture
)

PACKAGE_MAINTAINER=$(
    dpkg-deb -f "$DEB" Maintainer
)

PACKAGE_SECTION=$(
    dpkg-deb -f "$DEB" Section
)

PACKAGE_PRIORITY=$(
    dpkg-deb -f "$DEB" Priority
)

PACKAGE_DEPENDS=$(
    dpkg-deb -f "$DEB" Depends
)

PACKAGE_DESCRIPTION=$(
    dpkg-deb -f "$DEB" Description
)


# ============================================================
# Prüfen
# ============================================================

echo
echo "Package: $PACKAGE_NAME"
echo "Version: $PACKAGE_VERSION"
echo "Architecture: $PACKAGE_ARCHITECTURE"
echo


if [ "$PACKAGE_ARCHITECTURE" != "all" ]; then

    echo
    echo "FEHLER:"
    echo "Das Nova Pi Store Paket muss Architecture: all verwenden."
    echo

    exit 1

fi


# ============================================================
# Hashes
# ============================================================

echo "[5/8] Berechne Paket-Hashes..."


SIZE=$(
    stat -c%s "$DEB"
)

MD5=$(
    md5sum "$DEB" | awk '{print $1}'
)

SHA256=$(
    sha256sum "$DEB" | awk '{print $1}'
)


FILENAME="pool/main/$(basename "$DEB")"


# ============================================================
# Packages-Datei
# ============================================================

echo "[6/8] Erstelle Packages-Datei..."


PACKAGES_DIR="$REPO/dists/stable/main/binary-all"

PACKAGES_FILE="$PACKAGES_DIR/Packages"


cat > "$PACKAGES_FILE" <<EOF
Package: $PACKAGE_NAME
Version: $PACKAGE_VERSION
Architecture: $PACKAGE_ARCHITECTURE
Maintainer: $PACKAGE_MAINTAINER
Installed-Size: $(dpkg-deb -f "$DEB" Installed-Size)
Depends: $PACKAGE_DEPENDS
Section: $PACKAGE_SECTION
Priority: $PACKAGE_PRIORITY
Filename: $FILENAME
Size: $SIZE
MD5sum: $MD5
SHA256: $SHA256
Description: $PACKAGE_DESCRIPTION

EOF


# ============================================================
# Packages.gz
# ============================================================

echo "[7/8] Erstelle Packages.gz..."


gzip \
    -9 \
    -c "$PACKAGES_FILE" \
    > "$PACKAGES_DIR/Packages.gz"


# ============================================================
# Release-Datei
# ============================================================

echo "[8/8] Erstelle Release-Datei..."


RELEASE_FILE="$REPO/dists/stable/Release"


DATE=$(date -Ru)


cat > "$RELEASE_FILE" <<EOF
Origin: Nova Pi Store
Label: Nova Pi Store
Suite: stable
Codename: stable
Date: $DATE
Architectures: all
Components: main
Description: Nova Pi Store APT Repository
EOF


# ============================================================
# Installer
# ============================================================

if [ ! -f "$ROOT/scripts/install.sh" ]; then

    echo
    echo "FEHLER:"
    echo "scripts/install.sh wurde nicht gefunden."
    echo

    exit 1

fi


cp \
    "$ROOT/scripts/install.sh" \
    "$REPO/install.sh"


chmod 755 \
    "$REPO/install.sh"


# ============================================================
# Übersicht
# ============================================================

echo
echo "======================================"
echo "Repository erfolgreich erstellt"
echo "======================================"
echo

find "$REPO" \
    -type f \
    -print \
    | sort


echo
echo "======================================"
echo "Packages"
echo "======================================"
echo

cat "$PACKAGES_FILE"


echo
echo "======================================"
echo "Release"
echo "======================================"
echo

cat "$RELEASE_FILE"


echo
echo "======================================"
echo "Fertig"
echo "======================================"
