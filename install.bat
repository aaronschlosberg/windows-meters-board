@echo off
setlocal enabledelayedexpansion
title Master Meter - Full Installer

echo ========================================
echo   Master Meter - Full Installer
echo ========================================
echo Combines RAM / VRAM / GPU / CPU / Wattage / System Total
echo into one tray icon. Super simple install + migration.
echo.

REM Check for real Python
set "PYTHON="
for %%P in (
    "%LocalAppData%\Programs\Python\Python313\python.exe"
    "%LocalAppData%\Programs\Python\Python312\python.exe"
    "%LocalAppData%\Programs\Python\Python311\python.exe"
    "%LocalAppData%\Programs\Python\Python310\python.exe"
    "%ProgramFiles%\Python313\python.exe"
    "%ProgramFiles%\Python312\python.exe"
    "%ProgramFiles%\Python311\python.exe"
    "%ProgramFiles%\Python310\python.exe"
) do (
    if exist "%%~P" (
        set "PYTHON=%%~P"
        goto :havepython
    )
)

echo Python not found. Downloading and installing Python 3.12...
echo.

set "PY_INSTALLER=%TEMP%\python-3.12.7-amd64.exe"
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe' -OutFile '%PY_INSTALLER%'"
if errorlevel 1 (
    echo Download failed. Check your internet connection.
    pause
    exit /b 1
)

echo Installing Python (this may take a minute)...
"%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
if errorlevel 1 (
    echo Python install failed.
    pause
    exit /b 1
)

for /f "delims=" %%i in ('powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path','User')"') do set "PATH=%%i;%PATH%"

set "PYTHON=%LocalAppData%\Programs\Python\Python312\python.exe"
if not exist "%PYTHON%" (
    echo Python installed but not found at expected path.
    echo Please close this window, open a new Command Prompt, and run install.bat again.
    pause
    exit /b 1
)

:havepython
echo Found Python: %PYTHON%
echo.

echo Installing dependencies...
"%PYTHON%" -m pip install --upgrade pip -q
"%PYTHON%" -m pip install psutil pystray pillow nvidia-ml-py
if errorlevel 1 (
    echo Failed to install packages.
    pause
    exit /b 1
)

echo.
echo Creating / overwriting Startup shortcut...
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "PYTHONW=%PYTHON:python.exe=pythonw.exe%"
if not exist "%PYTHONW%" set "PYTHONW=%PYTHON%"

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; " ^
  "$s = $ws.CreateShortcut([Environment]::GetFolderPath('Startup') + '\Master Meter.lnk'); " ^
  "$s.TargetPath = '%PYTHONW%'; " ^
  "$s.Arguments = '\"%SCRIPT_DIR%\master_meter.py\"'; " ^
  "$s.WorkingDirectory = '%SCRIPT_DIR%'; " ^
  "$s.Save()"

echo.
echo Checking for existing single meters...
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "FOUND=0"
for %%F in (
    "RAM Meter.lnk"
    "CPU Meter.lnk"
    "Meters Board.lnk"
    "windows-ram-meter.lnk"
    "Hard Drive Meter.lnk"
) do (
    if exist "%STARTUP%\%%~F" (
        set "FOUND=1"
        echo Found: %%~F
    )
)

if "!FOUND!"=="1" (
    echo.
    echo Existing single meter shortcuts detected.
    set /p "MIGRATE=Remove them and collect under Master Meter? (Y/N): "
    if /i "!MIGRATE!"=="Y" (
        for %%F in (
            "RAM Meter.lnk"
            "CPU Meter.lnk"
            "Meters Board.lnk"
            "windows-ram-meter.lnk"
            "Hard Drive Meter.lnk"
        ) do (
            if exist "%STARTUP%\%%~F" del /q "%STARTUP%\%%~F"
        )
        echo Old shortcuts removed. Master Meter will take over on next login.
    ) else (
        echo Left existing meters in place. You can quit them manually later.
    )
) else (
    echo No existing single meter shortcuts found.
)

echo.
echo ========================================
echo   Done.
echo ========================================
echo Master Meter is installed and will start on next login.
echo Right-click the tray icon for menu. Left-click opens Task Manager.
echo.
echo To run it now:
echo   %PYTHONW% "%SCRIPT_DIR%\master_meter.py"
echo.
pause
