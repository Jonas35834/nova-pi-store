# 🍓 Nova Pi Store

**Nova Pi Store** ist eine einfache Web-App für **Raspberry Pi OS Lite**, mit der sich Programme bequem über eine Weboberfläche installieren und verwalten lassen.

Das Projekt richtet sich besonders an Raspberry Pis, die hauptsächlich über **SSH** verwaltet werden und keine Desktop-Umgebung besitzen.

---

## ✨ Funktionen

* 🌐 Weboberfläche
* 📦 Installation von Anwendungen
* 🗑️ Deinstallation von Anwendungen
* 🔄 Aktualisierung von Anwendungen
* 🔎 Suche nach Anwendungen
* 🏷️ Kategorien für Anwendungen
* 📊 Anzeige von Systeminformationen
* 🐧 Unterstützung für Raspberry Pi OS Lite
* 📦 Installation über APT
* 🤖 Automatischer Build über GitHub Actions
* 🌍 Eigenes APT-Repository über GitHub Pages

---

## 🖥️ Voraussetzungen

Nova Pi Store ist für folgende Umgebung gedacht:

* Raspberry Pi 3 oder neuer
* Raspberry Pi OS Lite
* Internetverbindung
* SSH-Zugriff
* Python 3
* APT

Eine grafische Desktop-Umgebung ist **nicht erforderlich**.

---

## 🚀 Installation

Die Installation kann direkt über das Internet gestartet werden.

Auf dem Raspberry Pi:

```bash
curl -fsSL https://jonas35834.github.io/nova-pi-store/install.sh | sudo bash
```

Der Installer richtet das Nova-Pi-Store-APT-Repository ein und installiert anschließend das Paket.

---

## 🌐 Weboberfläche

Nach der Installation läuft Nova Pi Store standardmäßig auf **Port 8080**.

Die IP-Adresse des Raspberry Pi kannst du mit folgendem Befehl herausfinden:

```bash
hostname -I
```

Anschließend kannst du die Weboberfläche im Browser öffnen:

```text
http://IP-ADRESSE-DES-PI:8080
```

Beispiel:

```text
http://192.168.178.50:8080
```

---

## 📦 APT-Repository

Das Nova-Pi-Store-Repository wird über GitHub Pages bereitgestellt:

**https://jonas35834.github.io/nova-pi-store/**

Nach der Einrichtung kann Nova Pi Store wie ein normales Debian-Paket über APT verwaltet werden.

### Aktualisieren

```bash
sudo apt update
sudo apt upgrade
```

### Installieren

```bash
sudo apt install nova-pi-store
```

### Deinstallieren

```bash
sudo apt remove nova-pi-store
```

---

## 🏗️ Projektstruktur

```text
nova-pi-store/
│
├── app/
│   └── ...
│
├── debian/
│   ├── control
│   ├── postinst
│   ├── prerm
│   └── nova-pi-store.service
│
├── scripts/
│   ├── build-deb.sh
│   ├── build-repository.sh
│   └── install.sh
│
├── .github/
│   └── workflows/
│       └── build.yml
│
└── README.md
```

---

## ⚙️ Systemdienst

Nova Pi Store läuft als **systemd-Dienst**:

```text
nova-pi-store.service
```

### Status anzeigen

```bash
systemctl status nova-pi-store
```

### Dienst neu starten

```bash
sudo systemctl restart nova-pi-store
```

### Dienst stoppen

```bash
sudo systemctl stop nova-pi-store
```

### Dienst starten

```bash
sudo systemctl start nova-pi-store
```

### Logs anzeigen

```bash
journalctl -u nova-pi-store
```

### Live-Logs anzeigen

```bash
journalctl -u nova-pi-store -f
```

---

## 📦 Debian-Paket

GitHub Actions erstellt automatisch ein Debian-Paket.

Beispiel:

```text
nova-pi-store_1.0.0_all.deb
```

Das Paket enthält unter anderem:

```text
/usr/share/nova-pi-store/
/lib/systemd/system/nova-pi-store.service
```

Die laufende Anwendung wird nach folgendem Verzeichnis installiert:

```text
/opt/nova-pi-store/
```

---

## 🤖 GitHub Actions

Bei einem Push auf den `main`-Branch wird automatisch ein Build gestartet.

Der Ablauf:

```text
Git Push
   │
   ▼
GitHub Actions
   │
   ├── Projekt prüfen
   │
   ├── Debian-Paket bauen
   │
   ├── APT-Repository erstellen
   │
   ├── GitHub Release erstellen
   │
   └── GitHub Pages aktualisieren
```

---

## 🌍 GitHub Pages

Das APT-Repository wird automatisch über GitHub Pages veröffentlicht.

### GitHub Repository

https://github.com/Jonas35834/nova-pi-store

### APT Repository

https://jonas35834.github.io/nova-pi-store/

---

## 🔐 Sicherheit

> ⚠️ **Hinweis:** Nova Pi Store befindet sich derzeit in Entwicklung.

Die aktuelle Testversion verwendet für das APT-Repository:

```text
[trusted=yes]
```

Dadurch wird die Paket-Signaturprüfung für dieses Repository deaktiviert.

Für eine spätere produktive Version ist eine **GPG-signierte APT-Quelle** geplant.

---

## 🗺️ Roadmap

### Version 1.0

* [x] Debian-Paket
* [x] GitHub Actions
* [x] GitHub Release
* [x] APT-Repository
* [x] GitHub Pages
* [x] Installationsskript
* [x] systemd-Service
* [ ] GPG-Signierung

### Version 1.1

* [ ] App-Liste
* [ ] App-Suche
* [ ] Kategorien
* [ ] Installieren-Button
* [ ] Deinstallieren-Button
* [ ] Update-Button
* [ ] Anzeige installierter Apps

### Version 1.2

* [ ] App-Beschreibungen
* [ ] App-Icons
* [ ] Versionsinformationen
* [ ] Speicherplatzanzeige
* [ ] CPU-Auslastung
* [ ] RAM-Auslastung
* [ ] Systeminformationen

### Version 2.0

* [ ] Modernere Benutzeroberfläche
* [ ] Erweiterte App-Verwaltung
* [ ] Mehrere Paketquellen
* [ ] GPG-Signierung
* [ ] Automatische Updates
* [ ] Erweiterte Raspberry-Pi-Unterstützung

---

## 👨‍💻 Entwickler

**Jonas35834**

### GitHub

https://github.com/Jonas35834

### Projekt

https://github.com/Jonas35834/nova-pi-store

---

## 📄 Lizenz

Das Projekt befindet sich derzeit in Entwicklung.
