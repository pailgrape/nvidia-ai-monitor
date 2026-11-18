#!/usr/bin/env python3
"""
Optional bridge: NVIDIA AI & Compute Monitor → 3.5" Rev A smart screen
(USB35INCHSV2 / QinHeng UsbMonitor / Turing 3.5" style)

Pushes a dense PowerMizer-style telemetry image over the Revision A serial protocol.
Canvas is fixed at 320x480 (portrait). Change WIDTH/HEIGHT and redraw layout for other sizes.
"""

import subprocess
import time
import serial
import struct
from PIL import Image, ImageDraw, ImageFont

# --- Screen (Rev A 3.5" / USB35INCHSV2) ---
WIDTH = 320
HEIGHT = 480
COM_PORT = "/dev/ttyACM0"  # or AUTO if you implement discovery; set to your port
BAUD = 115200

# Protocol constants (Revision A)
CMD_RESET = 101
CMD_CLEAR = 102
CMD_SCREEN_ON = 109
CMD_SET_BRIGHTNESS = 110
CMD_DISPLAY_BITMAP = 197

def send_reg(ser, cmd, x=0, y=0, ex=0, ey=0):
    buf = bytearray(6)
    buf[0] = (x >> 2) & 0xFF
    buf[1] = (((x & 3) << 6) + (y >> 4)) & 0xFF
    buf[2] = (((y & 15) << 4) + (ex >> 6)) & 0xFF
    buf[3] = (((ex & 63) << 2) + (ey >> 8)) & 0xFF
    buf[4] = ey & 0xFF
    buf[5] = cmd
    ser.write(buf)

def display_bitmap(ser, image):
    """Send a full-screen RGB image as RGB565 LE over Revision A protocol."""
    if image.size != (WIDTH, HEIGHT):
        image = image.resize((WIDTH, HEIGHT))
    image = image.convert("RGB")
    send_reg(ser, CMD_DISPLAY_BITMAP, 0, 0, WIDTH - 1, HEIGHT - 1)
    time.sleep(0.01)

    pix = image.load()
    line = bytearray()
    for h in range(HEIGHT):
        for w in range(WIDTH):
            r, g, b = pix[w, h]
            r = r >> 3
            g = g >> 2
            b = b >> 3
            rgb565 = (r << 11) | (g << 5) | b
            line += struct.pack("<H", rgb565)
        if len(line) >= WIDTH * 2 * 8:  # chunk roughly every few lines
            ser.write(line)
            line = bytearray()
    if line:
        ser.write(line)
    time.sleep(0.02)

def query_nvidia():
    """Pull key PowerMizer-style fields."""
    cmd = [
        "nvidia-smi",
        "--query-gpu=name,utilization.gpu,utilization.memory,memory.used,memory.total,"
        "temperature.gpu,power.draw,power.limit,clocks.sm,clocks.mem,pstate,fan.speed",
        "--format=csv,noheader,nounits"
    ]
    try:
        out = subprocess.check_output(cmd, text=True, timeout=2).strip()
        parts = [p.strip() for p in out.split(",")]
        if len(parts) >= 12:
            return {
                "name": parts[0],
                "gpu_util": int(parts[1] or 0),
                "mem_util": int(parts[2] or 0),
                "mem_used": int(parts[3] or 0),
                "mem_total": int(parts[4] or 1),
                "temp": int(parts[5] or 0),
                "power": float(parts[6] or 0),
                "power_limit": float(parts[7] or 1),
                "clock_sm": int(parts[8] or 0),
                "clock_mem": int(parts[9] or 0),
                "pstate": parts[10],
                "fan": int(parts[11] or 0),
            }
    except Exception:
        pass
    return None

def query_processes():
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader,nounits"],
            text=True, timeout=2
        ).strip()
        procs = []
        for line in out.splitlines()[:4]:  # top 4
            if line:
                procs.append(line)
        return procs
    except Exception:
        return []

def draw_dashboard(data, procs):
    img = Image.new("RGB", (WIDTH, HEIGHT), (15, 20, 30))
    draw = ImageDraw.Draw(img)

    # Try a small font; fall back to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except Exception:
        font = ImageFont.load_default()
        font_sm = font
        font_big = font

    y = 8
    draw.text((8, y), "NVIDIA AI Monitor", fill=(0, 245, 212), font=font_big)
    y += 28
    if data:
        draw.text((8, y), data["name"][:28], fill=(200, 200, 200), font=font_sm)
        y += 20

        # VRAM bar
        mem_pct = int(100 * data["mem_used"] / max(data["mem_total"], 1))
        draw.text((8, y), f"VRAM {data['mem_used']}/{data['mem_total']} MiB ({mem_pct}%)", fill=(255, 255, 255), font=font)
        y += 18
        draw.rectangle([8, y, WIDTH - 8, y + 12], outline=(80, 80, 80))
        draw.rectangle([9, y + 1, 9 + int((WIDTH - 18) * mem_pct / 100), y + 11], fill=(0, 180, 255))
        y += 22

        # GPU util
        draw.text((8, y), f"GPU {data['gpu_util']}%   MemBus {data['mem_util']}%", fill=(255, 255, 255), font=font)
        y += 18
        draw.rectangle([8, y, WIDTH - 8, y + 10], outline=(80, 80, 80))
        draw.rectangle([9, y + 1, 9 + int((WIDTH - 18) * data["gpu_util"] / 100), y + 9], fill=(0, 220, 120))
        y += 20

        # Temp / Power / Fan
        draw.text((8, y), f"Temp {data['temp']}°C   Fan {data['fan']}%", fill=(255, 200, 100), font=font)
        y += 18
        draw.text((8, y), f"Power {data['power']:.0f}/{data['power_limit']:.0f} W", fill=(255, 160, 80), font=font)
        y += 22

        # Clocks / P-State
        draw.text((8, y), f"P-State {data['pstate']}", fill=(180, 220, 255), font=font)
        y += 18
        draw.text((8, y), f"Core {data['clock_sm']} MHz", fill=(200, 200, 200), font=font_sm)
        y += 16
        draw.text((8, y), f"Mem  {data['clock_mem']} MHz", fill=(200, 200, 200), font=font_sm)
        y += 24
    else:
        draw.text((8, y), "nvidia-smi not available", fill=(255, 100, 100), font=font)
        y += 30

    # Processes
    draw.text((8, y), "Compute Processes:", fill=(0, 245, 212), font=font)
    y += 18
    if procs:
        for p in procs:
            draw.text((12, y), p[:40], fill=(220, 220, 220), font=font_sm)
            y += 16
    else:
        draw.text((12, y), "(none)", fill=(150, 150, 150), font=font_sm)

    return img

def main():
    print("NVIDIA smart-screen bridge (Rev A / USB35INCHSV2, 320x480)")
    print(f"Opening {COM_PORT} ...")
    try:
        ser = serial.Serial(COM_PORT, BAUD, timeout=1)
    except Exception as e:
        print(f"Failed to open serial port: {e}")
        print("Check /dev/ttyACM* and dialout group membership.")
        return

    # Init
    send_reg(ser, CMD_RESET)
    time.sleep(0.1)
    send_reg(ser, CMD_SCREEN_ON)
    send_reg(ser, CMD_SET_BRIGHTNESS, x=40)  # ~40%
    time.sleep(0.1)

    print("Pushing telemetry. Ctrl+C to stop.")
    try:
        while True:
            data = query_nvidia()
            procs = query_processes()
            img = draw_dashboard(data, procs)
            display_bitmap(ser, img)
            time.sleep(1.5)
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        ser.close()

if __name__ == "__main__":
    main()
