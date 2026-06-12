# Overhead — live flight track projection

A radar-style display of the **actual aircraft flying overhead right now**,
designed to be projected onto a wall or ceiling. A Raspberry Pi with an
RTL-SDR dongle decodes the ADS-B transmissions every airliner broadcasts on
1090 MHz; this server turns them into a dark, high-contrast track display with
trails, callsigns, altitudes, speeds and headings.

- **Zero dependencies** — pure Python 3 standard library; runs on a stock
  Raspberry Pi OS install. The frontend is vanilla HTML/JS/CSS, fully offline.
- **Two data sources** — a local `dump1090`/`readsb` receiver (real RF,
  no internet needed), with automatic fallback to the free
  [airplanes.live](https://airplanes.live) API so you can develop and demo
  before the hardware arrives.
- **Projector-friendly UI** — pure black background, phosphor-green radar,
  range rings, fading trails, a featured "OVERHEAD" card for the closest
  aircraft, fullscreen on click.

Hardware shopping list and signal-chain details: **[HARDWARE.md](HARDWARE.md)**.

## Quick start (no hardware needed)

```bash
# Set your location, then run — falls back to the public API automatically:
OVERHEAD_LAT=51.4700 OVERHEAD_LON=-0.4543 python3 run.py
# open http://localhost:8000  (click the page for fullscreen)
```

## With a receiver (Raspberry Pi + RTL-SDR)

```bash
sudo apt install -y dump1090-fa          # see HARDWARE.md
OVERHEAD_LAT=<your lat> OVERHEAD_LON=<your lon> OVERHEAD_SOURCE=dump1090 python3 run.py
```

## Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `OVERHEAD_LAT` / `OVERHEAD_LON` | 51.4700 / -0.4543 | Station (your) location — the centre of the radar. |
| `OVERHEAD_RADIUS_KM` | 60 | Radar range; aircraft beyond this are hidden. |
| `OVERHEAD_PORT` | 8000 | HTTP port for the display. |
| `OVERHEAD_SOURCE` | `auto` | `dump1090`, `api`, or `auto` (try local receiver, fall back to API). |
| `OVERHEAD_DUMP1090_URL` | `http://127.0.0.1:8080/data/aircraft.json` | Where the decoder publishes data. |
| `OVERHEAD_POLL_S` | 1.0 | Poll interval (min 5 s enforced for the public API). |
| `OVERHEAD_TRAIL_LEN` | 120 | Points kept per aircraft trail. |

## Run on boot (Raspberry Pi)

```bash
sudo ./deploy/install.sh        # installs + enables the systemd service
journalctl -u overhead -f      # watch logs
```

Then point the projector at Chromium in kiosk mode
(`chromium-browser --kiosk http://127.0.0.1:8000`) — `deploy/install.sh`
prints the exact autostart snippet.

## Development

```bash
python3 -m unittest discover -s tests -v
```

## Layout

```
overhead/        backend: config, geo math, data sources, tracker, HTTP server
static/          frontend: radar canvas + sidebar (vanilla JS/CSS)
deploy/          systemd unit + Raspberry Pi install script
tests/           stdlib unittest suite (no network required)
HARDWARE.md      bill of materials, receiver setup, placement tips
```
