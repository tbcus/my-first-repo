# Overhead — live flight track projection (API edition)

A radar-style display of the **actual aircraft flying overhead right now**,
designed to be projected onto a wall or ceiling. No receiver, no antenna,
no hardware beyond the machine running it: set your latitude/longitude and
the server pulls live traffic from the free, no-key
[airplanes.live](https://airplanes.live) API, then renders a dark,
high-contrast track display with trails, callsigns, altitudes, speeds and
headings.

- **Zero dependencies** — pure Python 3 standard library; runs on anything
  from a Raspberry Pi to a laptop. The frontend is vanilla HTML/JS/CSS.
- **No API key needed** — data comes from the free airplanes.live point
  API. Be polite: a 5 s minimum poll interval is enforced.
- **Projector-friendly UI** — pure black background, phosphor-green radar,
  range rings, fading trails, a featured "OVERHEAD" card for the closest
  aircraft, fullscreen on click.

## Quick start

```bash
# Set your location, then run:
OVERHEAD_LAT=51.4700 OVERHEAD_LON=-0.4543 python3 run.py
# open http://localhost:8000  (click the page for fullscreen)

# Completely offline? Use the built-in simulated traffic:
OVERHEAD_SOURCE=demo python3 run.py
```

## Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `OVERHEAD_LAT` / `OVERHEAD_LON` | 51.4700 / -0.4543 | Station (your) location — the centre of the radar. |
| `OVERHEAD_RADIUS_KM` | 60 | Radar range; aircraft beyond this are hidden. |
| `OVERHEAD_PORT` | 8000 | HTTP port for the display. |
| `OVERHEAD_SOURCE` | `api` | `api` (live data from airplanes.live) or `demo` (built-in simulated traffic, fully offline). |
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
```
