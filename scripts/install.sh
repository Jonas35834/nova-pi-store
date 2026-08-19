#!/bin/bash

set -e

REPO_URL="https://jonas35834.github.io/nova-pi-store"

echo
echo "======================================"
echo "🍓 Nova Pi Store Installer"
echo "======================================"
echo

echo "[1/4] Prüfe System..."

if [ "$(id -u)" -ne 0 ]; then
    echo "Dieses Skript muss als root ausgeführt werden."
    echo "Verwende:"
    echo
    echo "curl -fsSL $REPO_URL/install.sh | sudo bash"
    exit 1
fi

echo "✓ Root-Rechte vorhanden"

echo
echo "[2/4] Erstelle APT-Quelle..."

cat > /etc/apt/sources.list.d/nova-pi-store.list <<EOF
deb [trusted=yes] ${REPO_URL} stable main
EOF

echo "✓ APT-Quelle eingerichtet"

echo
echo "[3/4] Aktualisiere APT..."

apt-get update

echo
echo "[4/4] Installiere Nova Pi Store..."

apt-get install -y nova-pi-store

echo
echo "======================================"
echo "✓ Nova Pi Store wurde installiert"
echo "======================================"
echo

IP=$(hostname -I | awk '{print $1}')

echo "Weboberfläche:"
echo
echo "http://${IP}:8080"
echo
echo "Oder im Netzwerk:"
echo
echo "http://$(hostname).local:8080"
echo
