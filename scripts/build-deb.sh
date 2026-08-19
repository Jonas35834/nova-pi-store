#!/bin/bash

set -e


VERSION="${1:-1.0.0}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

BUILD="$ROOT/build"

OUTPUT="$ROOT/nova-pi-store_${VERSION}_all.deb"


rm -rf "$BUILD"

rm -f "$OUTPUT"


mkdir -p \
    "$BUILD/DEBIAN" \
    "$BUILD/usr/share/nova-pi-store" \
    "$BUILD/lib/systemd/system"


cp \
    "$ROOT/debian/control" \
    "$BUILD/DEBIAN/control"


cp \
    "$ROOT/debian/postinst" \
    "$BUILD/DEBIAN/postinst"


cp \
    "$ROOT/debian/prerm" \
    "$BUILD/DEBIAN/prerm"


cp \
    "$ROOT/debian/nova-pi-store.service" \
    "$BUILD/lib/systemd/system/"


cp -r \
    "$ROOT/app" \
    "$BUILD/usr/share/nova-pi-store/"


sed -i \
    "s/^Version: .*/Version: $VERSION/" \
    "$BUILD/DEBIAN/control"


chmod 755 \
    "$BUILD/DEBIAN/postinst"


chmod 755 \
    "$BUILD/DEBIAN/prerm"


dpkg-deb \
    --build \
    "$BUILD" \
    "$OUTPUT"


echo
echo "======================================"
echo "Nova Pi Store package created"
echo "======================================"
echo
echo "$OUTPUT"
