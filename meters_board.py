#!/usr/bin/env python3
"""
Windows Multi-Meter Board - System Tray Utility
Single process tray icon that displays one of: RAM / VRAM / GPU / CPU / Wattage
as a color-coded dial. Right-click menu to switch metric, view all in tooltip,
open Task Manager, see top processes, toggle refresh, quit.

Preserves RAM meter features. Low-resource (~single update thread).

Deps: psutil pystray pillow nvidia-ml-py (optional for GPU/VRAM/Watt)
"""

import psutil
import pystray
from PIL import Image, ImageDraw
import threading
import time
import subprocess

try:
    from pynvml import (
        nvmlInit, nvmlShutdown, nvmlDeviceGetCount,
        nvmlDeviceGetHandleByIndex, nvmlDeviceGetMemoryInfo,
        nvmlDeviceGetName, nvmlDeviceGetUtilizationRates,
        nvmlDeviceGetTemperature, nvmlDeviceGetPowerUsage,
        nvmlDeviceGetPowerManagementLimit, NVMLError,
        NVML_TEMPERATURE_GPU
    )
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False

# Config
REFRESH_INTERVAL = 2.0
THRESHOLDS = (70, 90)  # green <70, yellow <90, red (for %)
WATT_THRESHOLDS = (100, 200)  # absolute W for color when showing Wattage
GPU_INDEX = 0
SHOW_ALL_IN_TOOLTIP = True  # always show summary of all

METRICS = ["RAM", "VRAM", "GPU", "CPU", "Wattage"]
current_metric = "RAM"

# Energy tracking for Wattage (estimate)
cumulative_wh = 0.0
last_sample_time = None
last_power_w = 0.0

nvml_initialized = False
gpu_handle = None

def init_nvml():
    global nvml_initialized, gpu_handle
    if not NVML_AVAILABLE or nvml_initialized:
        return
    try:
        nvmlInit()
        nvml_initialized = True
        count = nvmlDeviceGetCount()
        if count > 0:
            gpu_handle = nvmlDeviceGetHandleByIndex(GPU_INDEX)
    except Exception:
        nvml_initialized = False
        gpu_handle = None

def create_image(value, is_watts=False):
    """Dial icon. value is percent (0-100) or watts if is_watts."""
    image = Image.new('RGB', (64, 64), color=(30, 30, 30))
    draw = ImageDraw.Draw(image)
    draw.ellipse((4, 4, 60, 60), outline=(100, 100, 100), width=2)

    if is_watts:
        color = (0, 255, 0) if value < WATT_THRESHOLDS[0] else (255, 165, 0) if value < WATT_THRESHOLDS[1] else (255, 0, 0)
        max_visual = 300.0
        pct = max(0, min(100, (value / max_visual) * 100))
        text = f"{int(value)}W"
        tx = 16 if value < 10 else 12 if value < 100 else 8
    else:
        pct = max(0, min(100, value))
        color = (0, 255, 0) if pct < THRESHOLDS[0] else (255, 165, 0) if pct < THRESHOLDS[1] else (255, 0, 0)
        text = f"{int(pct)}%"
        tx = 18 if pct < 10 else 14 if pct < 100 else 10

    angle = int(360 * pct / 100)
    draw.arc((8, 8, 56, 56), start=-90, end=-90 + angle, fill=color, width=6)
    draw.text((tx, 24), text, fill=(255, 255, 255))
    return image

def get_top_processes(n=3):
    procs = []
    for p in psutil.process_iter(['name', 'memory_info']):
        try:
            mem = p.info['memory_info'].rss / (1024 ** 2)
            procs.append((p.info['name'], mem))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda x: x[1], reverse=True)
    return procs[:n]

def collect_metrics():
    """Return dict of metric -> (display_value, is_watts, tooltip_line)"""
    data = {}

    # RAM
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    data["RAM"] = (
        mem.percent,
        False,
        f"RAM: {mem.percent:.1f}% | {mem.used/1e9:.1f}/{mem.total/1e9:.1f} GB | Avail {mem.available/1e9:.1f} | Swap {swap.used/1e9:.1f}"
    )

    # CPU
    cpu_pct = psutil.cpu_percent(interval=None)
    data["CPU"] = (
        cpu_pct,
        False,
        f"CPU: {cpu_pct:.1f}% | {psutil.cpu_count()} cores"
    )

    # GPU family (if available)
    if gpu_handle is not None:
        try:
            name = nvmlDeviceGetName(gpu_handle)
            if isinstance(name, bytes):
                name = name.decode('utf-8', errors='ignore').strip()
            else:
                name = str(name).strip()

            # VRAM
            meminfo = nvmlDeviceGetMemoryInfo(gpu_handle)
            vram_pct = (meminfo.used / meminfo.total * 100.0) if meminfo.total else 0
            data["VRAM"] = (
                vram_pct,
                False,
                f"VRAM: {vram_pct:.1f}% | {meminfo.used/1e9:.2f}/{meminfo.total/1e9:.1f} GB | {name}"
            )

            # GPU util + temp + power
            util = nvmlDeviceGetUtilizationRates(gpu_handle)
            gpu_util = util.gpu
            try:
                temp = nvmlDeviceGetTemperature(gpu_handle, NVML_TEMPERATURE_GPU)
            except Exception:
                temp = None
            try:
                power_mw = nvmlDeviceGetPowerUsage(gpu_handle)
                power_w = power_mw / 1000.0 if power_mw else 0.0
            except Exception:
                power_w = 0.0
            try:
                limit_mw = nvmlDeviceGetPowerManagementLimit(gpu_handle)
                limit_w = limit_mw / 1000.0 if limit_mw else None
            except Exception:
                limit_w = None

            temp_str = f" {temp}°C" if temp is not None else ""
            data["GPU"] = (
                gpu_util,
                False,
                f"GPU: {gpu_util:.0f}%{temp_str} | {power_w:.0f}W | {name}"
            )

            # Wattage (GPU power)
            limit_str = f"/{limit_w:.0f}W" if limit_w else ""
            data["Wattage"] = (
                power_w,
                True,
                f"Wattage: {power_w:.0f}W{limit_str} | Cumul ~{cumulative_wh:.1f} Wh | {name}"
            )
        except Exception:
            pass

    # Fallbacks if missing
    for m in ["VRAM", "GPU", "Wattage"]:
        if m not in data:
            data[m] = (0, m == "Wattage", f"{m}: N/A (no NVIDIA / NVML)")

    return data

def update_energy(power_w):
    global cumulative_wh, last_sample_time, last_power_w
    now = time.time()
    if last_sample_time is not None:
        dt_h = (now - last_sample_time) / 3600.0
        avg_w = (last_power_w + power_w) / 2.0
        cumulative_wh += avg_w * dt_h
    last_sample_time = now
    last_power_w = power_w

def update_icon(icon):
    global REFRESH_INTERVAL
    # Prime CPU
    psutil.cpu_percent(interval=None)
    while True:
        metrics = collect_metrics()
        val, is_w, _ = metrics.get(current_metric, (0, False, ""))
        if current_metric == "Wattage" and val > 0:
            update_energy(val)
        icon.icon = create_image(val, is_watts=is_w)

        # Tooltip
        if SHOW_ALL_IN_TOOLTIP:
            lines = [metrics[m][2] for m in METRICS if m in metrics]
            icon.title = " | ".join(lines)
        else:
            icon.title = metrics.get(current_metric, (0, False, current_metric))[2]

        time.sleep(REFRESH_INTERVAL)

def on_quit(icon, item):
    try:
        if nvml_initialized:
            nvmlShutdown()
    except Exception:
        pass
    icon.stop()

def on_toggle_refresh(icon, item):
    global REFRESH_INTERVAL
    REFRESH_INTERVAL = 1.0 if REFRESH_INTERVAL > 1.0 else 2.0
    item.text = f"Refresh: {REFRESH_INTERVAL:.1f}s"

def on_open_taskmgr(icon, item):
    subprocess.Popen(['taskmgr.exe'])

def on_switch_metric(metric):
    def _switch(icon, item):
        global current_metric
        current_metric = metric
        # Optional: update menu to reflect current (recreate)
        icon.menu = make_menu()
    return _switch

def on_toggle_all_tooltip(icon, item):
    global SHOW_ALL_IN_TOOLTIP
    SHOW_ALL_IN_TOOLTIP = not SHOW_ALL_IN_TOOLTIP
    item.text = f"All in tooltip: {'On' if SHOW_ALL_IN_TOOLTIP else 'Off'}"

def on_reset_wh(icon, item):
    global cumulative_wh, last_sample_time
    cumulative_wh = 0.0
    last_sample_time = None

def make_menu():
    metric_items = [
        pystray.MenuItem(
            f"{'● ' if m == current_metric else '  '}{m}",
            on_switch_metric(m)
        )
        for m in METRICS
    ]
    top = get_top_processes(3)
    top_items = [pystray.MenuItem(f"{name}: {mem:.0f} MB", lambda i, it: None) for name, mem in top]

    return pystray.Menu(
        pystray.MenuItem("Switch Metric", pystray.Menu(*metric_items)),
        pystray.MenuItem(f"All in tooltip: {'On' if SHOW_ALL_IN_TOOLTIP else 'Off'}", on_toggle_all_tooltip),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Open Task Manager", on_open_taskmgr),
        pystray.MenuItem("Top Processes", pystray.Menu(*top_items)) if top_items else pystray.MenuItem("Top Processes", lambda i, it: None),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(f"Refresh: {REFRESH_INTERVAL:.1f}s", on_toggle_refresh),
        pystray.MenuItem("Reset Wh counter", on_reset_wh),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit)
    )

def setup(icon):
    init_nvml()
    icon.visible = True
    icon.menu = make_menu()
    threading.Thread(target=update_icon, args=(icon,), daemon=True).start()

if __name__ == "__main__":
    icon = pystray.Icon("Meters", create_image(0), "Meters Board", make_menu())
    icon.run(setup)
