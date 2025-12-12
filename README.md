# ReNightdive Wad Manager

![ReNight Icon](https://github.com/Retzilience/ReNight/raw/assets/imgs/ReNight.png)

**ReNight** (or **ReNightdive Wad Manager**) is an open-source GUI application for managing local DOOM `.wad` mods for Nightdive’s **DOOM + DOOM II (KEX 2024)** port. It provides a straightforward workflow for importing WADs into the game’s local mod folder using either copying or symbolic linking, and it includes basic mod list management utilities.

---

## Quick Download (v0.3)

**Windows**  
[ReNight_windows_0.3.zip](https://github.com/Retzilience/ReNight/releases/download/0.3/ReNight_windows_0.3.zip)

**Linux**  
[ReNight_linux_0.3.tar.gz](https://github.com/Retzilience/ReNight/releases/download/0.3/ReNight_linux_0.3.tar.gz)

**All releases**  
[GitHub Releases (latest)](https://github.com/Retzilience/ReNight/releases/latest)

---

## Features

- **Nightdive Folder selection**: Set the folder where the KEX port loads local mods (ReNight attempts to auto-detect it on first run, including common Steam/Proton layouts).
- **PWADs Folder selection**: Set a root folder where you keep your WADs for browsing and for improved source matching.
- **Import modes**:
  - **Symlink mode**: Create symlinks into the Nightdive folder (saves disk space; requires symlink support on your OS).
  - **Copy mode**: Copy WADs into the Nightdive folder (does not modify your originals).
- **Safer copy collision handling**: When importing in copy mode and a filename collision exists with different content, ReNight generates a unique destination name (`name-2.wad`, `name-3.wad`, …) instead of overwriting unrelated files.
- **Improved mod list UI**: Mods are displayed in a two-column table (filename + status tag). Multi-select delete is supported.
- **More reliable mod classification**:
  - `(SL)` for symlink entries.
  - `(CPY)` for copied entries that can be associated back to a source file (via stored metadata and/or filename+MD5 matching within the PWAD tree).
  - `(ONL)` for entries that exist only in the Nightdive folder (manual additions, imports from outside the PWAD tree, or missing/moved sources).
- **Filesystem monitoring**: Watches the Nightdive folder and the selected PWAD folder tree and refreshes the mod list automatically when content changes.
- **Update checking**: ReNight can compare its version against a small descriptor file and then open either the GitHub Releases page or a direct download link in the system browser.
- **Per-user config and state**: Configuration and mod metadata are stored in OS-appropriate per-user locations rather than beside the executable, with automatic migration from legacy side-by-side files on first run.

![Windows UI](https://github.com/Retzilience/ReNight/raw/assets/imgs/ui_v03.png)
![Game UI](https://github.com/Retzilience/ReNight/raw/assets/imgs/game.png)

### Example: Symlinked Eviternity II

![Symlink Example](https://github.com/Retzilience/ReNight/raw/assets/imgs/working_sl.gif)

---

## Table of Contents

- [Installation](#installation)
  - [Windows](#windows)
  - [Linux](#linux)
- [Usage](#usage)
  - [Running the Application](#running-the-application)
  - [Mod Import Options](#mod-import-options)
  - [Symbolic Linking](#symbolic-linking)
- [Notes](#notes)
- [License](#license)
- [Credits](#credits)

---

## Installation

## Windows

### Option 1: Download the latest release (recommended)

1. Visit [GitHub Releases (latest)](https://github.com/Retzilience/ReNight/releases/latest).
2. Download [ReNight_windows_0.3.zip](https://github.com/Retzilience/ReNight/releases/download/0.3/ReNight_windows_0.3.zip).
3. Extract it to a folder of your choice.
4. Run `ReNight.exe`.

### Option 2: Run from source

1. Install Python 3.10.6+.
2. Clone the repository:

    ```shell
    git clone https://github.com/Retzilience/ReNight.git
    cd ReNight
    ```

3. Create and activate a virtual environment:

    ```shell
    python -m venv venv
    venv\Scripts\activate
    ```

4. Install dependencies:

    ```shell
    pip install -r requirements.txt
    ```

5. Run the application:

    ```shell
    python ReNight.pyw
    ```

### Option 3: Build from source (Nuitka)

As of v0.3, distributed binaries are compiled with **Nuitka** (native binaries generated via a C/C++ toolchain).

---

## Linux

### Finding the Nightdive folder (Steam/Proton)

On Linux under Steam/Proton, the Nightdive local mod directory is typically under `compatdata`. A common path layout is:

`~/.local/share/Steam/steamapps/compatdata/2280/pfx/drive_c/users/steamuser/Saved Games/Nightdive Studios/DOOM`

If you are having problems, launch the game and use: **Mods → Play → Open Local Mod Folder** to open the correct directory.

### Option 1: Download the compiled release (recommended)

1. Visit [GitHub Releases (latest)](https://github.com/Retzilience/ReNight/releases/latest).
2. Download [ReNight_linux_0.3.tar.gz](https://github.com/Retzilience/ReNight/releases/download/0.3/ReNight_linux_0.3.tar.gz).
3. Extract:

    ```shell
    tar -xzvf ReNight_linux_0.3.tar.gz
    ```

4. Run:

    ```shell
    ./ReNight
    ```

### Option 2: Run from source

1. Ensure Python 3 and venv tooling are installed:

    ```shell
    sudo apt update
    sudo apt install python3 python3-pip python3-venv
    ```

2. Clone the repository:

    ```shell
    git clone https://github.com/Retzilience/ReNight.git
    cd ReNight
    ```

3. Create and activate a virtual environment:

    ```shell
    python3 -m venv venv
    source venv/bin/activate
    ```

4. Install dependencies:

    ```shell
    pip install -r requirements.txt
    ```

5. Run the application:

    ```shell
    python3 ReNight.pyw
    ```

---

## Usage

### Running the Application

After launching, the main window provides options to select folders, import WADs, and view current mods in the Nightdive folder.

### Mod Import Options

- **Pick WAD**: Select one or more WAD files to import.
- **Pick Folder (Batch)**: Select a folder and import every `.wad` in that directory.
- **Import**: Creates either symlinks or copies according to your settings.

### Symbolic Linking

When enabled, ReNight creates a symbolic link inside the Nightdive Folder that points to the original WAD in your PWAD tree. If disabled, ReNight copies the WAD into the Nightdive Folder.

---

## Notes

- The Nightdive KEX in-game UI is limited to single-WAD local mods. Multi-WAD setups still require custom launch methods outside ReNight.
- Formats not supported by KEX (for example `.pk3` and typical “ZDoom mods”) are not made compatible by ReNight.
- “Compressed containers” (for example WADs inside `.zip`) are not supported by the KEX local mod loader and therefore are not supported by ReNight.

---

## License

This project is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License. For details, visit: <http://creativecommons.org/licenses/by-nc-sa/4.0/>

---

## Credits

Made by **retzilience**.

Special thanks to **RataUnderground** for the app icon.
