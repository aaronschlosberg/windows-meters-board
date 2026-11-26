# Master Meter (extended from Meters Board)

Single-process Windows system tray utility that combines:

- **RAM**
- **VRAM** (NVIDIA)
- **GPU** (util / temp / power)
- **CPU** (short rolling average so spikes show but don't dominate)
- **Wattage** (GPU power + cumulative Wh)
- **System Total** (shows the single highest-taxed resource right now)

One tray icon. Right-click to choose which meter is displayed, select which are available, open Options, or Quit.  
Left-click / double-click opens Task Manager (Performance preferred).

## Super simple install + migration

1. Download the zip from the Drive folder or extract from repo.
2. Double-click `install.bat`.
   - Auto-installs Python 3.12 if missing.
   - Installs all dependencies.
   - Creates/overwrites Startup shortcut for Master Meter.
   - Detects existing single-meter shortcuts (RAM Meter, CPU Meter, Meters Board, etc.) and offers to remove them so they collect under the master.

New installs cleanly overwrite any previous Master Meter shortcut.

## Options window

- Choose displayed meter
- Check which meters are available
- Refresh rate: 0.5 / 1 / 2 / 4 s (default 1 s, matches Task Manager Normal)
- Color thresholds
- Start with Windows toggle

Config saved to `%APPDATA%\WindowsMasterMeter\config.json`.

## Manual run

```
pythonw master_meter.py
```

## Requirements

- Windows 10/11
- NVIDIA GPU + driver for VRAM / GPU / Wattage (others work without)
- Python 3.10+ (installer handles it)

Low-resource: single update thread, optional NVML.

Full source is in the shareable zip: G:\My Drive\_AI_Master_Folder\Grok\Development - Extensions and Small Apps\master-meter.zip

Based on the earlier windows-ram-meter and meters-board.
