# Smart-screen Bridge (Revision A)

Optional package that pushes NVIDIA AI & Compute Monitor telemetry to a **3.5″ Revision A** smart screen.

## Target hardware

This bridge is written for the classic **USB35INCHSV2** / QinHeng Electronics **UsbMonitor** (VID `1a86`, PID `5722`) family — the same protocol used by the original Turing Smart Screen 3.5″ and UsbPCMonitor clones.

- Resolution: **320 × 480** (portrait)
- Protocol: Revision A serial (the COM layer used by [turing-smart-screen-python](https://github.com/mathoudebine/turing-smart-screen-python) for these models)
- Typical device names: USB35INCHIPS / USB35INCHIPSV2 / UsbMonitor

Other Turing / TURZX sizes and revisions (B, C, D, pure USB, etc.) use different protocols and resolutions. This package does **not** target them.

## Linux permissions

The screen appears as a serial device (`/dev/ttyACM0` or similar). Add your user to the `dialout` group and re-login:

```bash
sudo usermod -aG dialout $USER
```

## What it shows

A dense PowerMizer-style panel updated every ~1.5 s:

- GPU name
- VRAM used / total + bar
- GPU core and memory-bus utilization
- Core temperature and fan %
- Power draw / limit
- P-State
- Core and memory clocks
- Top compute processes (PID + VRAM)

The layout is intentionally compact so the same data the desktop GUI collects fits on the small panel while you run offline token / Stability Matrix workloads.

## Requirements

- The screen connected and appearing as a serial device
- User in the `dialout` group
- Python packages: `pyserial`, `Pillow` (see `requirements.txt`)
- Working `nvidia-smi`

```bash
pip install -r requirements.txt
```

## Run

Edit `COM_PORT` at the top of `bridge.py` if needed, then:

```bash
cd smart-screen
python3 bridge.py
```

Ctrl+C to stop. The screen stays at the last frame.

## Adapting canvas size

The drawing code is fixed at `WIDTH = 320`, `HEIGHT = 480`.  
To target a different resolution later (other Rev A sizes or a rotated layout):

1. Change the two constants.
2. Adjust the text/bar coordinates in `draw_dashboard()` as needed.

No other protocol code has to change for pure dimension tweaks. Full support for non-Rev-A models would require a different communication layer (see the Turing project examples for those protocols).

## Upstream credit

The Revision A serial protocol implemented in `bridge.py` is a minimal re-implementation based on public documentation and reference code from:

- **[mathoudebine/turing-smart-screen-python](https://github.com/mathoudebine/turing-smart-screen-python)** (GPL-3.0)

Full credit for the protocol research and the original driver goes to that project and its contributors. This bridge only contains a small subset of the communication commands needed to push a full-screen bitmap; it does not redistribute any of the upstream source.

## Relation to the main project

This folder is completely optional. The desktop `ai-monitor-gui.py` remains zero-dependency and unchanged. Use the bridge only when you want the physical 3.5″ screen as a dedicated active monitor for compute loads.
