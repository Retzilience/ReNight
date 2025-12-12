---
# ReNightdive Wad Manager

![ReNight Icon](https://github.com/Retzilience/ReNight/raw/assets/imgs/ReNight.png)

**ReNight** (also known as **ReNightdive Wad Manager**) is an open-source GUI application for managing local DOOM `.wad` mods for Nightdive’s **DOOM + DOOM II (KEX 2024)** port.

ReNight exists because the in-game path for loading “local mods” involves uploading them through the game UI. Many users do not want to upload files they did not create, and they want a strictly local workflow. The only purely local alternative is to manually drop WADs into the Nightdive local mod folder and then keep that folder maintained by hand. ReNight provides a standalone importer and manager that keeps that folder organized using either copies or symbolic links.

---

## Download

**Latest release (recommended):**  
[GitHub Releases (latest)](https://github.com/Retzilience/ReNight/releases/latest)

**Quick download (v0.3):**
- **Windows:** [ReNight_windows_0.3.zip](https://github.com/Retzilience/ReNight/releases/download/0.3/ReNight_windows_0.3.zip)
- **Linux:** [ReNight_linux_0.3.tar.gz](https://github.com/Retzilience/ReNight/releases/download/0.3/ReNight_linux_0.3.tar.gz)

**All releases:**  
[GitHub Releases](https://github.com/Retzilience/ReNight/releases)

---

## Getting started

### Windows

1. Download from: [GitHub Releases (latest)](https://github.com/Retzilience/ReNight/releases/latest) (choose the **Windows** `.zip`).
2. Extract the `.zip` anywhere (for example, a folder on your Desktop).
3. Run `ReNight.exe`.

### Linux

1. Download from: [GitHub Releases (latest)](https://github.com/Retzilience/ReNight/releases/latest) (choose the **Linux** `.tar.gz`).
2. Extract it:

   ```shell
   tar -xzf ReNight_linux_<version>.tar.gz
   ```

3. Run it:

   ```shell
   ./ReNight
   ```

If your file manager blocks execution, set the executable bit:

```shell
chmod +x ReNight
```

---

## What it does

ReNight manages WAD files inside the Nightdive local mod folder by importing from a “PWADs folder” (your own library folder).

You choose one import mode:

- **Symlink mode:** ReNight creates a symbolic link in the Nightdive folder that points to the original WAD inside your PWADs folder.
- **Copy mode:** ReNight copies the WAD into the Nightdive folder.

ReNight does not modify WAD contents. It only manages filesystem entries.

### Intended workflow

ReNight is optimized for a common “Doomer library” setup: a single PWAD root folder containing many WADs arranged in any subfolder structure (for example, `megawads/`, `mapsets/`, `gameplay/`, etc.). ReNight can import from almost any structure, but its quality-of-life features are designed around selecting a PWAD root once and then repeatedly importing from that library.

When ReNight needs to associate a file in the Nightdive folder back to a source file (for example, for copy-mode tracking), it uses stored metadata and/or filename+MD5 matching within the PWAD tree.

---

## Terminology

**WAD / PWAD:** For practical purposes here, a “WAD” is a `.wad` file you want to load as a local mod.

**Symlink (symbolic link):** A filesystem entry that looks like a normal file but redirects to another file. It saves disk space and keeps the Nightdive folder “mirroring” your library.

On Windows, creating symlinks can require Administrator rights or enabling Developer Mode (depending on system policy and environment). On Linux, symlinks generally work normally, but they can still be affected by filesystem permissions and mount options.

---

## Features

- **Nightdive folder selection:** Set the folder where the KEX port loads local mods. ReNight attempts to auto-detect it on first run (including common Steam/Proton layouts).
- **PWADs folder selection:** Set a root folder where you keep your WADs for browsing and for improved source matching.
- **Import modes:**
  - **Symlink mode:** Create symlinks into the Nightdive folder (saves disk space; depends on symlink support/permissions).
  - **Copy mode:** Copy WADs into the Nightdive folder (does not modify your originals).
- **Safer copy collision handling:** If importing in copy mode and a filename collision exists with different content, ReNight generates a unique destination name (`name-2.wad`, `name-3.wad`, …) instead of overwriting unrelated files.
- **Improved mod list UI:** Mods are displayed in a two-column table (filename + status tag). Multi-select delete is supported.
- **More reliable mod classification:**
  - `(SL)` for symlink entries.
  - `(CPY)` for copied entries that can be associated back to a source file (via stored metadata and/or filename+MD5 matching within the PWAD tree).
  - `(ONL)` for entries that exist only in the Nightdive folder (manual additions, imports from outside the PWAD tree, or missing/moved sources).
- **Filesystem monitoring:** Watches the Nightdive folder and the selected PWAD folder tree and refreshes the mod list automatically when content changes.
- **Update checking:** ReNight can compare its version against a small descriptor file and then open either the GitHub Releases page or a direct download link in the system browser.
- **Per-user config and state:** Configuration and mod metadata are stored in OS-appropriate per-user locations rather than beside the executable, with automatic migration from legacy side-by-side files on first run.

![Windows UI](https://github.com/Retzilience/ReNight/raw/assets/imgs/ui_v03.png)
![Game UI](https://github.com/Retzilience/ReNight/raw/assets/imgs/game.png)

### Example: Symlinked Eviternity II

![Symlink Example](https://github.com/Retzilience/ReNight/raw/assets/imgs/working_sl.gif)

---

## Notes and limitations

- The Nightdive KEX in-game UI is limited to single-WAD local mods. Multi-WAD setups still require custom launch methods outside ReNight.
- Formats not supported by KEX (for example `.pk3` and typical “ZDoom mods”) are not made compatible by ReNight.
- “Compressed containers” (for example WADs inside `.zip`) are not supported by the KEX local mod loader and therefore are not supported by ReNight.

---

## Finding the Nightdive local mod folder

### Windows (typical)

The folder is under your user profile in “Saved Games” (Nightdive Studios). The exact path can vary.

If you are unsure, launch the game and use: **Mods → Play → Open Local Mod Folder** to open the correct directory, then copy that path into ReNight.

### Linux (Steam/Proton)

On Linux under Steam/Proton, the Nightdive local mod directory is typically under `compatdata`. A common layout is:

```text
~/.local/share/Steam/steamapps/compatdata/2280/pfx/drive_c/users/steamuser/Saved Games/Nightdive Studios/DOOM
```

If you are unsure, launch the game and use: **Mods → Play → Open Local Mod Folder**.

---

## Usage

After launching, the main window provides options to select folders, import WADs, and view current mods in the Nightdive folder.

### Import actions

- **Pick WAD:** Select one or more WAD files to import.
- **Pick Folder (Batch):** Select a folder and import every `.wad` in that directory.
- **Import:** Creates either symlinks or copies according to your settings.

### Deleting mods

The list supports multi-selection delete. Deleting from ReNight removes entries from the Nightdive folder. In symlink mode, this removes the link only (not your original WAD). In copy mode, this removes the copied file only (not your original WAD).

---

## Installation from source (Python)

ReNight is developed and packaged with **Python 3.11** as the baseline. Running from source requires Python 3.11+.

The current entry point for running from source is:

- `renight_entry.py`

### Windows: run from source

1. Install **Python 3.11**.
2. Install **Git** (optional, but recommended).
3. Clone the repository:

   ```powershell
   git clone https://github.com/Retzilience/ReNight.git
   cd ReNight
   ```

4. Create and activate a virtual environment:

   ```powershell
   py -3.11 -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

5. Install dependencies:

   ```powershell
   python -m pip install -U pip
   python -m pip install -r requirements.txt
   ```

6. Run:

   ```powershell
   python .\renight_entry.py
   ```

If PowerShell blocks activation scripts, you can run the venv Python directly without activation:

```powershell
.\venv\Scripts\python.exe -m pip install -U pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe .\renight_entry.py
```

### Linux: run from source

1. Install Python 3.11, venv, pip, and Git using your distro tooling.

   Debian/Ubuntu:

   ```shell
   sudo apt update
   sudo apt install -y python3.11 python3.11-venv python3-pip git
   ```

   Fedora:

   ```shell
   sudo dnf install -y python3 python3-pip git
   ```

   Arch:

   ```shell
   sudo pacman -S --needed python python-pip git
   ```

2. Clone the repository:

   ```shell
   git clone https://github.com/Retzilience/ReNight.git
   cd ReNight
   ```

3. Create and activate a virtual environment:

   ```shell
   python3.11 -m venv venv
   source venv/bin/activate
   ```

4. Install dependencies and run:

   ```shell
   python -m pip install -U pip
   python -m pip install -r requirements.txt
   python ./renight_entry.py
   ```

---

## Building binaries from source (Nuitka)

Distributed binaries are compiled with **Nuitka** (native binaries generated via a C/C++ toolchain).

The commands below assume you are running them from the repository root and that `renight_entry.py` is the entry point (as used in packaged builds).

### Common prerequisites

- Python 3.11
- `pip` and `venv`
- A working C/C++ toolchain
- Nuitka installed into your build environment

If you ship `requirements-build.txt`, install it in the build venv:

```shell
python -m pip install -r requirements-build.txt
```

### Windows: build (example command used for releases)

This is the build command used as of v0.3 (PowerShell). It assumes `ReNight.ico` exists in the working directory.

```powershell
& "C:\Program Files\Python311\python.exe" -m nuitka `
  --mode=onefile `
  --windows-console-mode=disable `
  --mingw64 `
  --assume-yes-for-downloads `
  --enable-plugin=pyside6 `
  --include-qt-plugins=sensible `
  --windows-icon-from-ico=ReNight.ico `
  --output-filename=ReNight.exe `
  renight_entry.py
```

Toolchain notes (Windows):

- `--mingw64` tells Nuitka to use MinGW64. With `--assume-yes-for-downloads`, Nuitka can download its preferred toolchain components when needed.
- If your environment blocks developer features, symlink creation at runtime may require running the application elevated or enabling Windows Developer Mode.

### Linux: build (example command used for releases)

```shell
python -m nuitka \
  --mode=onefile \
  --enable-plugin=pyside6 \
  --include-qt-plugins=sensible \
  --output-filename=ReNight \
  renight_entry.py
```

Toolchain notes (Linux):

- You need a compiler toolchain installed. Typical packages are `gcc`, `g++`, and `make` (often provided by `build-essential` on Debian/Ubuntu).
- Some distros require additional packaging utilities for binary patching. If Nuitka reports missing tools, install what it requests via your package manager.

---

## License

This project is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License. For details, visit: <http://creativecommons.org/licenses/by-nc-sa/4.0/>

---

## Credits

Made by **retzilience**.

Special thanks to **RataUnderground** for the app icon.
