#!/bin/bash

set -e

REPO_URL="https://jonas35834.github.io/nova-pi-store"

echo "======================================"
echo "🍓 Nova Pi Store Installer"
echo "======================================"
echo

echo "[1/3] Erstelle APT-Quelle..."

cat > /etc/apt/sources.list.d/nova-pi-store.list <<EOF
deb [trusted=yes] ${REPO_URL} stable main
EOF

echo "[2/3] Aktualisiere APT..."

apt-get update

echo "[3/3] Installiere Nova Pi Store..."

apt-get install -y nova-pi-store

echo
echo "======================================"
echo "✓ Nova Pi Store installiert"
echo "======================================"
echo
echo "Weboberfläche:"
echo
echo "http://$(hostname -I | awk '{print $1}'):8080"
echo
