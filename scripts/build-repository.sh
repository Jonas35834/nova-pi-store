#!/bin/bash

set -e

VERSION="${1:-1.0.0}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

REPO="$ROOT/apt-repository"

DEB="$ROOT/nova-pi-store_${VERSION}_all.deb"

PACKAGE_NAME="nova-pi-store"

echo "======================================"
echo "Nova Pi Store APT Repository"
echo "======================================"
echo

rm -rf "$REPO"

mkdir -p \
    "$REPO/pool/main" \
    "$REPO/dists/stable/main/binary-all"


echo "[1/5] Copy Debian package..."

cp \
    "$DEB" \
    "$REPO/pool/main/"


echo "[2/5] Read Debian package information..."

PACKAGE_INFO=$(dpkg-deb -f "$DEB")


echo "[3/5] Generate Packages file..."

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

print(packages)
PY


echo "[4/5] Compress Packages..."

gzip -9 -k \
    "$REPO/dists/stable/main/binary-all/Packages"


echo "[5/5] Create Release file..."

cat > "$REPO/dists/stable/Release" <<EOF
Origin: Nova Pi Store
Label: Nova Pi Store
Suite: stable
Codename: stable
Architectures: all
Components: main
Description: Nova Pi Store APT Repository
EOF


echo
echo "======================================"
echo "Repository created successfully"
echo "======================================"
echo

find "$REPO" -type f | sort
