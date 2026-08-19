#!/bin/bash

set -e

VERSION="${1:-1.0.0}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

REPO="$ROOT/apt-repository"

DEB="$ROOT/nova-pi-store_${VERSION}_all.deb"


echo "======================================"
echo "Nova Pi Store APT Repository"
echo "======================================"
echo

rm -rf "$REPO"

mkdir -p \
    "$REPO/pool/main" \
    "$REPO/dists/stable/main/binary-all"


echo "[1/4] Copy Debian package..."

cp \
    "$DEB" \
    "$REPO/pool/main/"


echo "[2/4] Generate Packages..."

cd "$REPO"

dpkg-scanpackages \
    pool/main \
    /dev/null \
    > dists/stable/main/binary-all/Packages


echo "[3/4] Compress Packages..."

gzip -9 -k \
    dists/stable/main/binary-all/Packages


echo "[4/4] Create Release file..."

cat > dists/stable/Release <<EOF
Origin: Nova Pi Store
Label: Nova Pi Store
Suite: stable
Codename: stable
Architectures: all
Components: main
Description: Nova Pi Store APT Repository
EOF


echo
echo "Repository created:"
echo

find "$REPO" -type f | sort

echo
echo "DONE"
