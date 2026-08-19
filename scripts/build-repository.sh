#!/bin/bash

set -e

VERSION="${1:-1.0.0}"

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


# --------------------------------------------------
# Repository löschen
# --------------------------------------------------

rm -rf "$REPO"


# --------------------------------------------------
# Verzeichnisstruktur erstellen
# --------------------------------------------------

mkdir -p \
    "$REPO/pool/main" \
    "$REPO/dists/stable/main/binary-all"


# --------------------------------------------------
# Debian-Paket kopieren
# --------------------------------------------------

echo "[1/6] Kopiere Debian-Paket..."

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


# --------------------------------------------------
# Paketinformationen lesen
# --------------------------------------------------

echo "[2/6] Lese Paketinformationen..."

PACKAGE_INFO=$(dpkg-deb -f "$DEB")


# --------------------------------------------------
# Packages-Datei erzeugen
# --------------------------------------------------

echo "[3/6] Erstelle Packages-Datei..."

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


relative = (
    "pool/main/" +
    deb.name
)


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


# --------------------------------------------------
# Packages komprimieren
# --------------------------------------------------

echo "[4/6] Komprimiere Packages..."

gzip \
    -9 \
    -k \
    "$REPO/dists/stable/main/binary-all/Packages"


# --------------------------------------------------
# Release-Datei
# --------------------------------------------------

echo "[5/6] Erstelle Release-Datei..."

cat > "$REPO/dists/stable/Release" <<EOF
Origin: Nova Pi Store
Label: Nova Pi Store
Suite: stable
Codename: stable
Architectures: all
Components: main
Description: Nova Pi Store APT Repository
EOF


# --------------------------------------------------
# Installer kopieren
# --------------------------------------------------

echo "[6/6] Kopiere Installer..."

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


# --------------------------------------------------
# Übersicht
# --------------------------------------------------

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
echo "Fertig"
echo "======================================"
