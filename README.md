# NVIDIA AI & Compute Monitor GUI

A lightweight, zero-dependency Linux desktop telemetry dashboard for **NVIDIA GPUs and Compute Cards** (GeForce, Workstation, Tesla, and Mining/Compute editions). Built for monitoring local AI and compute workloads.

![License: MIT](https://img.shields.io/badge/License-MIT-00F5D4.svg)
![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-00BBF9.svg)
![Platform: Linux](https://img.shields.io/badge/Platform-Linux%20(X11%20%2F%20Wayland)-0B131E.svg)

---

## Key Features

* **Zero Pip Dependencies:** Uses Python's standard `tkinter` library and system `nvidia-smi` / `nvidia-settings` utilities—no virtual environments or heavy Electron wrappers required.
* **Real-Time Telemetry Bars:** Live progress bars with dynamic color thresholds for:
  * **VRAM Allocation** (`MiB` used / total & `%`)
  * **GPU Core & Memory Bus Utilization** (`%`)
  * **Core Temperature** (`°C`) & **Fan Speed** (`%`)
  * **Board Power Draw** (`W` vs. TDP limit)
* **AI & Compute Diagnostics:**
  * Displays **Active P-State (`P0`–`P8`)**, **PowerMizer Level**, **Core/Memory Clocks (`MHz`)**, **PCIe Link Generation/Width**, and **Architecture / Compute Capability**.
  * Decodes hex `clocks_event_reasons` into human-readable statuses (`Optimal`, `Idle Clocks`, `Thermal Throttle`, `Power Cap`).
* **Local Process Detection:**
  * Lists running CUDA/PyTorch processes along with their `PID` and exact VRAM footprint.
* **One-Click Performance & Fan Control:**
  * **Lock Max Perf + Fan:** Enables Persistence Mode (`nvidia-smi -pm 1`), sets PowerMizer to *Prefer Maximum Performance*, and locks a custom fan speed (`30%`–`100%`).
  * **Safe Auto-Reset:** Clicking **Reset Auto** or closing the window automatically restores Adaptive PowerMizer and automatic BIOS fan control.

---

## Hardware Compatibility

| GPU Family | Examples | Support Status |
| :--- | :--- | :--- |
| **Pascal (CC 6.x)** | GTX 1060–1080 Ti, Tesla P40 | Full Support |
| **Turing (CC 7.5)** | RTX 2060–2080 Ti, Quadro RTX, T4 | Full Support |
| **Ampere (CC 8.x)** | RTX 3060–3090 Ti, A4000–A6000, A100 | Full Support |
| **Ada Lovelace (CC 8.9)** | RTX 4060–4090, L4, L40S | Full Support |
| **Hopper / Blackwell (CC 9.0+)** | H100, H200, RTX 50-series | Full Support |

*Note: Passively cooled data-center GPUs without physical fans (e.g., Tesla P40, A100, H100) gracefully report `0 %` fan speed while retaining full VRAM, thermal, power, and process telemetry.*

---

## Requirements & Installation

1. **NVIDIA Proprietary Drivers** (`nvidia-smi` available in `PATH`).
2. **Python 3** with `tkinter`:
   * **Fedora / RHEL:** `sudo dnf install python3-tkinter`
   * **Ubuntu / Debian / Mint:** `sudo apt install python3-tk`
   * **Arch / EndeavourOS / Manjaro:** `sudo pacman -S tk`

### Clone & Run

```bash
git clone https://github.com/pailgrape/nvidia-ai-monitor.git
cd nvidia-ai-monitor
chmod +x ai-monitor-gui.py
python3 ai-monitor-gui.py
```

### Optional: Install as a Global Terminal Command

Run the included installer to symlink `ai-monitor` into `~/.local/bin` so you can launch it from anywhere in the terminal:

```bash
chmod +x install.sh
./install.sh
ai-monitor
```

---

## Optional: Smart-screen Bridge

An optional `smart-screen/` package pushes the same telemetry to a **3.5″ Revision A** USB smart screen (USB35INCHSV2 / QinHeng UsbMonitor).  
It is completely separate from the desktop GUI and only needed if you want a dedicated physical panel for compute loads.  
See [smart-screen/README.md](smart-screen/README.md) for details.

---

## License

Released under the [MIT License](LICENSE).
