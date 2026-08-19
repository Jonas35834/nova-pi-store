# 🍓 Nova Pi Store

A lightweight web-based application store for Raspberry Pi OS Lite.

## Features

- Web interface
- Raspberry Pi OS Lite support
- APT application installation
- Search
- Categories
- Installation output
- Installed-app detection
- Debian package
- GitHub Actions builds

## Architecture

Nova Pi Store consists of:

- Python
- Flask
- HTML
- CSS
- JavaScript
- Debian packaging
- systemd

## Development

Run:

```bash
python3 app/app.py
````

Then open:

```text
http://localhost:8080
```

## Build Debian package

```bash
chmod +x scripts/build-deb.sh

./scripts/build-deb.sh
```

The result will be:

```text
nova-pi-store_1.0.0_all.deb
```

## Installation

```bash
sudo apt install ./nova-pi-store_1.0.0_all.deb
```

The web interface runs on:

```text
http://RASPBERRY-PI-IP:8080
```

## App database

Applications are defined in:

```text
app/apps.json
```

Example:

```json
{
    "id": "nginx",
    "name": "Nginx",
    "description": "Webserver",
    "icon": "🌐",
    "category": "Server",
    "type": "apt",
    "packages": ["nginx"]
}
```

Only predefined APT package names are allowed.

## License

MIT
