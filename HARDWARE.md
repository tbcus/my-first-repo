# Hardware Specification — "Flights Overhead" Projection Display

This build receives **real ADS-B transmissions** broadcast by aircraft on
1090 MHz, decodes them locally, and projects a live radar-style track display
onto a wall or ceiling. No internet connection or API key is required once the
receiver is running (the software falls back to a free public API only when no
receiver is attached, e.g. while you wait for parts).

## Bill of materials

| # | Part | Recommended model | Approx. price | Notes |
|---|------|-------------------|---------------|-------|
| 1 | Single-board computer | **Raspberry Pi 4 (2 GB)** or Pi 5 | $45–60 | Pi 3B+ also works. Needs one free USB port + HDMI out. |
| 2 | microSD card | 32 GB A1-class (SanDisk/Samsung) | $8 | Raspberry Pi OS Lite (64-bit) or Desktop. |
| 3 | Power supply | Official Pi USB-C PSU, 5 V/3 A (5 A for Pi 5) | $10 | Undervoltage causes SDR dropouts — don't skimp here. |
| 4 | ADS-B receiver (SDR) | **FlightAware Pro Stick Plus** (best: built-in amp + 1090 MHz filter) or RTL-SDR Blog V4 | $20–30 | Any RTL2832U dongle works; the Pro Stick Plus noticeably improves range. |
| 5 | Antenna | 1090 MHz tuned antenna, SMA, ~5 dBi (e.g. FlightAware 26" or AirNav 1090 stick) | $15–45 | Even the small whip bundled with RTL-SDR kits will see 30–80 km. Mount high, near a window or outdoors. |
| 6 | Coax / adapter | SMA male–male, RG-58 ≤ 5 m (or SMA→MCX pigtail depending on dongle) | $8 | Keep coax short — loss at 1 GHz is significant. |
| 7 | Projector | Any 1080p projector, ≥ 200 ANSI lumens for a dark room (e.g. mini LED projector) | $80+ | The UI is black-background, so even cheap projectors look great. An HDMI monitor/TV works identically. |
| 8 | Optional: bandpass filter | 1090 MHz SAW filter | $20 | Only needed near strong FM/cell towers and only if your dongle has no built-in filter. |

**Total: roughly $190–250** with a budget projector, or **~$110** if you already
have a screen.

## Optional upgrades

- **Outdoor antenna + LMR-400 coax** — pushes reception to 250–400 km.
- **Raspberry Pi PoE+ HAT** — single-cable install in an attic/roof space.
- **978 MHz (UAT) second dongle** — adds US general-aviation traffic.
- **Short-throw projector mounted on a bookshelf** — ceiling "planetarium" mode:
  aim it straight up and the radar display matches the real sky above you
  (display is north-up; orient the projector so the top of the image faces north).

## How the signal chain works

```
aircraft transponder (1090 MHz, ~every 0.5 s)
        │  Mode S / ADS-B "extended squitter": ICAO hex, callsign,
        ▼  GPS position, altitude, speed, heading, vertical rate
antenna ─► SMA coax ─► RTL-SDR dongle ─► USB ─► Raspberry Pi
                                                  │
                                       readsb / dump1090-fa (decoder)
                                                  │  aircraft.json (1 Hz)
                                                  ▼
                                       this repo: overhead tracker server
                                                  │  http://pi:8000
                                                  ▼
                                       projector / browser in kiosk mode
```

## Receiver software (on the Pi)

```bash
# Raspberry Pi OS — install the decoder (either of these):
sudo apt update && sudo apt install -y dump1090-fa     # FlightAware build
# or: https://github.com/wiedehopf/adsb-scripts (readsb, recommended)

# Verify it's decoding (you should see aircraft within ~30 s):
curl http://127.0.0.1:8080/data/aircraft.json | head
```

Then follow [README.md](README.md) to run the display server, and point the
projector at a browser in kiosk mode:

```bash
chromium-browser --kiosk --noerrdialogs http://127.0.0.1:8000
```

## Placement tips

- ADS-B is line-of-sight: every metre of antenna height matters more than any
  electronics upgrade.
- Keep the dongle on a short USB extension away from the Pi to reduce
  USB-bus RF noise.
- A ground plane (even a metal cookie tin under a mag-mount whip) adds
  measurable range.
