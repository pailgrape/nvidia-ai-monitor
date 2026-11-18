#!/usr/bin/env python3
"""
NVIDIA AI & Compute Monitor GUI
Lightweight, zero-dependency Linux desktop telemetry dashboard for NVIDIA GPUs.
Uses tkinter + nvidia-smi / nvidia-settings.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import time
import re
import os
import sys
from datetime import datetime

# ---------- helpers ----------
def run_cmd(cmd, timeout=5):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), -1

def parse_nvidia_smi():
    """Query key metrics via nvidia-smi."""
    query = (
        "nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu,"
        "utilization.memory,temperature.gpu,fan.speed,power.draw,power.limit,"
        "clocks.current.graphics,clocks.current.memory,pstate,clocks_throttle_reasons.active,"
        "pci.bus_id,compute_cap --format=csv,noheader,nounits"
    )
    out, err, code = run_cmd(query)
    if code != 0 or not out:
        return None
    # Assume single GPU for simplicity; take first line
    parts = [p.strip() for p in out.split(",")]
    if len(parts) < 15:
        return None
    try:
        data = {
            "name": parts[0],
            "mem_total": float(parts[1]),
            "mem_used": float(parts[2]),
            "util_gpu": float(parts[3]),
            "util_mem": float(parts[4]),
            "temp": float(parts[5]),
            "fan": float(parts[6]) if parts[6] != "[N/A]" else 0.0,
            "power": float(parts[7]),
            "power_limit": float(parts[8]),
            "clock_core": float(parts[9]),
            "clock_mem": float(parts[10]),
            "pstate": parts[11],
            "throttle": parts[12],
            "bus_id": parts[13],
            "cc": parts[14],
        }
        data["mem_pct"] = (data["mem_used"] / data["mem_total"] * 100) if data["mem_total"] else 0
        data["power_pct"] = (data["power"] / data["power_limit"] * 100) if data["power_limit"] else 0
        return data
    except Exception:
        return None

def get_processes():
    out, err, code = run_cmd("nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader,nounits")
    procs = []
    if code == 0 and out:
        for line in out.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                try:
                    procs.append({
                        "pid": parts[0],
                        "name": parts[1],
                        "vram": float(parts[2]),
                    })
                except:
                    pass
    return procs

def decode_throttle(reasons):
    if not reasons or reasons in ("[N/A]", "N/A", "0x0000000000000000"):
        return "Optimal"
    mapping = {
        "0x0000000000000001": "Idle Clocks",
        "0x0000000000000002": "Application Clock Setting",
        "0x0000000000000004": "SW Power Cap",
        "0x0000000000000008": "HW Slowdown",
        "0x0000000000000010": "Sync Boost",
        "0x0000000000000020": "SW Thermal Slowdown",
        "0x0000000000000040": "HW Thermal Slowdown",
        "0x0000000000000080": "HW Power Brake Slowdown",
        "0x0000000000000100": "Display Clock Setting",
    }
    # simple match
    for hexval, label in mapping.items():
        if hexval in reasons:
            return label
    return reasons

def get_powermizer():
    out, _, _ = run_cmd("nvidia-settings -q GPUPowerMizerMode 2>/dev/null | grep Attribute | head -1")
    if "1" in out or "Prefer Maximum" in out:
        return "Prefer Maximum Performance"
    if "2" in out or "Adaptive" in out:
        return "Adaptive"
    return "Unknown"

# ---------- GUI ----------
class NvidiaMonitor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NVIDIA AI & Compute Monitor")
        self.geometry("920x680")
        self.configure(bg="#0B131E")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.running = True
        self.fan_locked = False
        self.custom_fan = 60

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#0B131E")
        style.configure("TLabel", background="#0B131E", foreground="#E0E6ED", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#00F5D4")
        style.configure("Metric.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("Accent.TButton", foreground="#0B131E", background="#00F5D4")

        # Header
        header = ttk.Label(self, text="NVIDIA AI & Compute Monitor", style="Header.TLabel")
        header.pack(pady=(12, 4))
        self.status_var = tk.StringVar(value="Initializing...")
        ttk.Label(self, textvariable=self.status_var).pack()

        # Main metrics frame
        metrics = ttk.Frame(self)
        metrics.pack(fill="both", expand=True, padx=16, pady=8)

        # Left column - bars
        left = ttk.Frame(metrics)
        left.pack(side="left", fill="both", expand=True, padx=8)

        self.bars = {}
        self.bar_labels = {}
        bar_specs = [
            ("vram", "VRAM", 0, 100),
            ("gpu", "GPU Core %", 0, 100),
            ("mem", "Memory Bus %", 0, 100),
            ("temp", "Temperature \u00b0C", 0, 100),
            ("fan", "Fan Speed %", 0, 100),
            ("power", "Power Draw % of TDP", 0, 100),
        ]
        for key, label, mn, mx in bar_specs:
            row = ttk.Frame(left)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=label, width=22, anchor="w").pack(side="left")
            bar = ttk.Progressbar(row, orient="horizontal", length=280, mode="determinate", maximum=100)
            bar.pack(side="left", padx=6)
            val = ttk.Label(row, text="--", width=28, anchor="w")
            val.pack(side="left")
            self.bars[key] = bar
            self.bar_labels[key] = val

        # Right column - diagnostics
        right = ttk.Frame(metrics)
        right.pack(side="right", fill="both", expand=True, padx=8)
        ttk.Label(right, text="Diagnostics", style="Header.TLabel").pack(anchor="w")
        self.diag_vars = {}
        diag_fields = [
            "GPU Name", "P-State", "PowerMizer", "Core Clock", "Memory Clock",
            "PCIe Link", "Compute Cap", "Throttle Status", "Last Update"
        ]
        for f in diag_fields:
            row = ttk.Frame(right)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=f + ":", width=16, anchor="w").pack(side="left")
            var = tk.StringVar(value="\u2014")
            ttk.Label(row, textvariable=var, style="Metric.TLabel").pack(side="left")
            self.diag_vars[f] = var

        # Processes
        ttk.Label(self, text="Active Compute Processes", style="Header.TLabel").pack(anchor="w", padx=16)
        proc_frame = ttk.Frame(self)
        proc_frame.pack(fill="both", expand=True, padx=16, pady=4)
        self.proc_tree = ttk.Treeview(proc_frame, columns=("pid", "name", "vram"), show="headings", height=6)
        self.proc_tree.heading("pid", text="PID")
        self.proc_tree.heading("name", text="Process")
        self.proc_tree.heading("vram", text="VRAM (MiB)")
        self.proc_tree.column("pid", width=80)
        self.proc_tree.column("name", width=360)
        self.proc_tree.column("vram", width=120)
        self.proc_tree.pack(fill="both", expand=True)

        # Controls
        ctrl = ttk.Frame(self)
        ctrl.pack(fill="x", padx=16, pady=12)
        ttk.Label(ctrl, text="Fan lock %:").pack(side="left")
        self.fan_spin = ttk.Spinbox(ctrl, from_=30, to=100, width=5, increment=5)
        self.fan_spin.set(60)
        self.fan_spin.pack(side="left", padx=4)
        ttk.Button(ctrl, text="Lock Max Perf + Fan", command=self.lock_max).pack(side="left", padx=8)
        ttk.Button(ctrl, text="Reset Auto", command=self.reset_auto).pack(side="left", padx=4)
        ttk.Button(ctrl, text="Refresh Now", command=self.update_all).pack(side="left", padx=4)

        # Start polling
        self.after(500, self.poll)

    def color_bar(self, bar, value, thresholds=(50, 80)):
        # ttk Progressbar doesn't easily recolor; we rely on system theme
        bar["value"] = min(max(value, 0), 100)

    def update_all(self):
        data = parse_nvidia_smi()
        if not data:
            self.status_var.set("nvidia-smi unavailable or no GPU detected")
            return
        self.status_var.set(f"Monitoring: {data['name']}")

        # Bars
        self.color_bar(self.bars["vram"], data["mem_pct"])
        self.bar_labels["vram"].config(text=f"{data['mem_used']:.0f} / {data['mem_total']:.0f} MiB ({data['mem_pct']:.1f}%)")
        self.color_bar(self.bars["gpu"], data["util_gpu"])
        self.bar_labels["gpu"].config(text=f"{data['util_gpu']:.0f} %")
        self.color_bar(self.bars["mem"], data["util_mem"])
        self.bar_labels["mem"].config(text=f"{data['util_mem']:.0f} %")
        self.color_bar(self.bars["temp"], data["temp"])
        self.bar_labels["temp"].config(text=f"{data['temp']:.0f} \u00b0C")
        self.color_bar(self.bars["fan"], data["fan"])
        self.bar_labels["fan"].config(text=f"{data['fan']:.0f} %")
        self.color_bar(self.bars["power"], data["power_pct"])
        self.bar_labels["power"].config(text=f"{data['power']:.1f} / {data['power_limit']:.0f} W")

        # Diagnostics
        self.diag_vars["GPU Name"].set(data["name"])
        self.diag_vars["P-State"].set(data["pstate"])
        self.diag_vars["PowerMizer"].set(get_powermizer())
        self.diag_vars["Core Clock"].set(f"{data['clock_core']:.0f} MHz")
        self.diag_vars["Memory Clock"].set(f"{data['clock_mem']:.0f} MHz")
        self.diag_vars["PCIe Link"].set(data["bus_id"])
        self.diag_vars["Compute Cap"].set(data["cc"])
        self.diag_vars["Throttle Status"].set(decode_throttle(data["throttle"]))
        self.diag_vars["Last Update"].set(datetime.now().strftime("%H:%M:%S"))

        # Processes
        for i in self.proc_tree.get_children():
            self.proc_tree.delete(i)
        for p in get_processes():
            self.proc_tree.insert("", "end", values=(p["pid"], p["name"], f"{p['vram']:.0f}"))

    def poll(self):
        if self.running:
            self.update_all()
            self.after(2000, self.poll)

    def lock_max(self):
        try:
            fan = int(self.fan_spin.get())
        except:
            fan = 60
        fan = max(30, min(100, fan))
        cmds = [
            "nvidia-smi -pm 1",
            "nvidia-settings -a GPUPowerMizerMode=1",
            f"nvidia-settings -a GPUTargetFanSpeed={fan}",
        ]
        for c in cmds:
            run_cmd(c)
        self.fan_locked = True
        self.custom_fan = fan
        messagebox.showinfo("Locked", f"Persistence on, PowerMizer=Max, Fan locked to {fan}%")

    def reset_auto(self):
        cmds = [
            "nvidia-settings -a GPUPowerMizerMode=2",  # Adaptive
            "nvidia-settings -a GPUTargetFanSpeed=0",  # Auto (0 often means auto)
        ]
        for c in cmds:
            run_cmd(c)
        self.fan_locked = False
        messagebox.showinfo("Reset", "Restored Adaptive PowerMizer and automatic fan control")

    def on_close(self):
        self.running = False
        if self.fan_locked:
            self.reset_auto()
        self.destroy()

if __name__ == "__main__":
    app = NvidiaMonitor()
    app.mainloop()
