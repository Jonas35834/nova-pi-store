#!/bin/bash

set -e

VERSION="${1:-1.1.0}"

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
# Debian-Paket kopieren
# ============================================================

echo "[3/8] Kopiere Debian-Paket..."

if [ ! -f "$DEB" ]; then

    echo
    echo "FEHLER:"
    echo "Debian-Paket nicht gefunden:"
    echo "$DEB"
    echo

    exit 1

fi

cp \
    "$DEB" \
    "$REPO/pool/main/"


# ============================================================
# Paketinformationen
# ============================================================

echo "[4/8] Lese Paketinformationen..."

python3 <<PY

import subprocess
from pathlib import Path

deb = Path("$DEB")
repo = Path("$REPO")

output = subprocess.check_output(
    ["dpkg-deb", "-f", str(deb)],
    text=True
)

fields = {}

for line in output.splitlines():

    if ": " in line:

        key, value = line.split(": ", 1)

        fields[key] = value


size = deb.stat().st_size


md5 = subprocess.check_output(
    ["md5sum", str(deb)],
    text=True
).split()[0]


sha256 = subprocess.check_output(
    ["sha256sum", str(deb)],
    text=True
).split()[0]


relative = "pool/main/" + deb.name


packages = f"""Package: {fields["Package"]}
Version: {fields["Version"]}
Architecture: {fields["Architecture"]}
Maintainer: {fields["Maintainer"]}
Installed-Size: {fields.get("Installed-Size", "")}
Depends: {fields.get("Depends", "")}
Section: {fields.get("Section", "")}
Priority: {fields.get("Priority", "")}
Filename: {relative}
Size: {size}
MD5sum: {md5}
SHA256: {sha256}
Description: {fields.get("Description", "")}

"""


packages_file = (
    repo /
    "dists/stable/main/binary-all/Packages"
)


packages_file.write_text(
    packages,
    encoding="utf-8"
)


print()
print(packages)

PY


# ============================================================
# Packages.gz
# ============================================================

echo "[5/8] Erstelle Packages.gz..."

gzip \
    -9 \
    -c \
    "$REPO/dists/stable/main/binary-all/Packages" \
    > "$REPO/dists/stable/main/binary-all/Packages.gz"


# ============================================================
# Release-Datei vorbereiten
# ============================================================

echo "[6/8] Erstelle Release-Datei..."

cd "$REPO/dists/stable"


DATE="$(date -Ru)"

PACKAGES_SIZE=$(stat -c%s main/binary-all/Packages)
PACKAGES_GZ_SIZE=$(stat -c%s main/binary-all/Packages.gz)

PACKAGES_MD5=$(md5sum main/binary-all/Packages | awk '{print $1}')
PACKAGES_GZ_MD5=$(md5sum main/binary-all/Packages.gz | awk '{print $1}')

PACKAGES_SHA256=$(sha256sum main/binary-all/Packages | awk '{print $1}')
PACKAGES_GZ_SHA256=$(sha256sum main/binary-all/Packages.gz | awk '{print $1}')


cat > Release <<EOF
Origin: Nova Pi Store
Label: Nova Pi Store
Suite: stable
Codename: stable
Date: $DATE
Architectures: all
Components: main
Description: Nova Pi Store APT Repository

MD5Sum:
 $PACKAGES_MD5 $PACKAGES_SIZE main/binary-all/Packages
 $PACKAGES_GZ_MD5 $PACKAGES_GZ_SIZE main/binary-all/Packages.gz

SHA256:
 $PACKAGES_SHA256 $PACKAGES_SIZE main/binary-all/Packages
 $PACKAGES_GZ_SHA256 $PACKAGES_GZ_SIZE main/binary-all/Packages.gz
EOF


# ============================================================
# Installer kopieren
# ============================================================

echo "[7/8] Kopiere Installer..."

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
echo "[8/8] Repository prüfen..."
echo

cd "$ROOT"

find "$REPO" \
    -type f \
    -print \
    | sort


echo
echo "======================================"
echo "Repository erfolgreich erstellt"
echo "======================================"
echo
echo "Version: $VERSION"
echo
