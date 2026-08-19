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

echo "[1/6] Kopiere Debian control..."

cp "$ROOT/debian/control" \
   "$BUILD/DEBIAN/control"

echo "[2/6] Kopiere Maintainer-Skripte..."

cp "$ROOT/debian/postinst" \
   "$BUILD/DEBIAN/postinst"

cp "$ROOT/debian/prerm" \
   "$BUILD/DEBIAN/prerm"

echo "[3/6] Kopiere systemd Service..."

cp "$ROOT/debian/nova-pi-store.service" \
   "$BUILD/lib/systemd/system/nova-pi-store.service"

echo "[4/6] Kopiere Anwendung..."

cp -r "$ROOT/app" \
      "$BUILD/usr/share/nova-pi-store/app"

echo "[5/6] Setze Berechtigungen..."

chmod 755 "$BUILD/DEBIAN/postinst"
chmod 755 "$BUILD/DEBIAN/prerm"

sed -i \
    "s/^Version: .*/Version: $VERSION/" \
    "$BUILD/DEBIAN/control"

echo
echo "Debian control:"
echo "--------------------------------------"
cat "$BUILD/DEBIAN/control"
echo "--------------------------------------"
echo

echo "[6/6] Erstelle Debian-Paket..."

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
