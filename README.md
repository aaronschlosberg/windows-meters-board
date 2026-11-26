# Windows Meters Board

Lightweight single-process system tray utility for Windows.

One tray icon. Right-click to switch the displayed dial between:

- **RAM** (system memory + swap, top processes)
- **VRAM** (NVIDIA GPU memory)
- **GPU** (utilization, temp, power)
- **CPU** (overall utilization)
- **Wattage** (NVIDIA GPU power draw + cumulative Wh estimate)

Color-coded dials (green / yellow / red). Tooltip can show all metrics at once.

## Super easy install

1. Download the zip and extract.
2. Double-click `install.bat`.
   - Auto-detects or silently installs Python 3.12 (adds to user PATH).
   - Installs dependencies.
   - Creates a Startup shortcut (pythonw, no console window).

The tray icon appears on next login (or run the pythonw command shown at the end of install).

## Manual run

```
pythonw meters_board.py
```

## Requirements

- Windows 10/11
- NVIDIA GPU + driver (for VRAM / GPU / Wattage; others work without)
- Python 3.10+ (installer handles it)

## Features preserved from RAM meter

- Top processes list
- Open Task Manager
- Refresh rate toggle (1s / 2s)
- Low resource usage

Menu also includes reset for the Wattage cumulative counter and toggle for "all metrics in tooltip".

Source: single file `meters_board.py` + `install.bat`.
