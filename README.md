# ALIENTEK T90 Logo Tool

Modern open-source GUI for preparing and flashing a custom **160×40 px** logo to the **ALIENTEK T90** soldering iron over USB HID.

## Features

- Drag & drop images
- Automatic 160×40 conversion
- Pixel-accurate 4× preview
- USB HID flashing
- Automatic system-language detection
- Ukrainian, English, Polish, German, French, Spanish and Czech
- Linux and Windows builds
- Linux `.deb` package
- GitHub Actions release builds

## Device

- USB VID:PID: `19F5:3245`
- Logo size: `160×40 px`
- Transport: USB HID

## Important

This repository expects the already-tested `t90_flash.py` from the working T90 project. Keep that file unchanged and place it in the repository root when building.

## Local Linux build

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Then place `t90_flash.py` in the repository root and build:

```bash
.venv/bin/pyinstaller \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --name Alientek-T90-Logo-Tool \
  --add-data "t90_flash.py:." \
  --add-data "assets:assets" \
  --hidden-import=hid \
  --collect-all hid \
  main.py
```

## Windows

GitHub Actions builds the Windows x64 executable on a hosted Windows runner. A Windows PC is not required for the maintainer.

## License

MIT
