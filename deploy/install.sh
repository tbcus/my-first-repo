#!/usr/bin/env bash
# Install the overhead display server as a systemd service on a Raspberry Pi.
# Usage: sudo ./deploy/install.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run with sudo: sudo $0" >&2
  exit 1
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR=/opt/overhead

echo "Installing from $REPO_DIR to $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"
cp -r "$REPO_DIR/overhead" "$REPO_DIR/static" "$REPO_DIR/run.py" "$INSTALL_DIR/"

cp "$REPO_DIR/deploy/overhead.service" /etc/systemd/system/overhead.service
systemctl daemon-reload
systemctl enable --now overhead.service

echo
echo "Service running. Check:   systemctl status overhead"
echo "Logs:                     journalctl -u overhead -f"
echo "Display:                  http://$(hostname -I | awk '{print $1}'):8000"
echo
echo "Edit your station location in /etc/systemd/system/overhead.service"
echo "(OVERHEAD_LAT / OVERHEAD_LON), then: sudo systemctl daemon-reload && sudo systemctl restart overhead"
echo
echo "To autostart the projector display (Raspberry Pi OS Desktop), add to"
echo "~/.config/wayfire.ini or ~/.config/lxsession/LXDE-pi/autostart:"
echo "  chromium-browser --kiosk --noerrdialogs --disable-restore-session-state http://127.0.0.1:8000"
