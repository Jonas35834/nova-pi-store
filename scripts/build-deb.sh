#!/bin/bash

set -e

VERSION="${1:-1.0.0}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/build"
OUTPUT="$ROOT/nova-pi-store_${VERSION}_all.deb"

echo "======================================"
echo "Nova Pi Store Debian Builder"
echo "======================================"
echo
echo "Root:    $ROOT"
echo "Version: $VERSION"
echo

rm -rf "$BUILD"
rm -f "$OUTPUT"

mkdir -p "$BUILD/DEBIAN"
mkdir -p "$BUILD/usr/share/nova-pi-store"
mkdir -p "$BUILD/lib/systemd/system"

echo "[1/7] Kopiere Debian control..."

cp "$ROOT/debian/control" \
   "$BUILD/DEBIAN/control"


echo "[2/7] Kopiere Maintainer-Skripte..."

cp "$ROOT/debian/postinst" \
   "$BUILD/DEBIAN/postinst"

cp "$ROOT/debian/prerm" \
   "$BUILD/DEBIAN/prerm"


echo "[3/7] Kopiere systemd Services..."

cp "$ROOT/debian/nova-pi-store.service" \
   "$BUILD/lib/systemd/system/nova-pi-store.service"

cp "$ROOT/debian/nova-pi-store-agent.service" \
   "$BUILD/lib/systemd/system/nova-pi-store-agent.service"


echo "[4/7] Kopiere Web-App..."

cp -r "$ROOT/app" \
      "$BUILD/usr/share/nova-pi-store/app"


echo "[5/7] Kopiere Agent..."

cp -r "$ROOT/agent" \
      "$BUILD/usr/share/nova-pi-store/agent"


echo "[6/7] Setze Berechtigungen..."

chmod 755 "$BUILD/DEBIAN/postinst"
chmod 755 "$BUILD/DEBIAN/prerm"

chmod 755 \
    "$BUILD/usr/share/nova-pi-store/agent/agent.py"


sed -i \
    "s/^Version: .*/Version: $VERSION/" \
    "$BUILD/DEBIAN/control"


echo
echo "Debian control:"
echo "--------------------------------------"

cat "$BUILD/DEBIAN/control"

echo "--------------------------------------"
echo

echo "[7/7] Erstelle Debian-Paket..."

dpkg-deb \
    --build \
    --root-owner-group \
    "$BUILD" \
    "$OUTPUT"


echo
echo "======================================"
echo "BUILD ERFOLGREICH"
echo "======================================"
echo
echo "Paket:"
echo "$OUTPUT"
echo
