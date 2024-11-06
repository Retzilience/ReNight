# ReNightdive Wad Manager

ReNightdive Wad Manager is a Python-based GUI application designed to help you manage DOOM WAD mods for Nightdive's 'DOOM + DOOM II' KEX 2024 sourceport. This tool provides a user-friendly interface for organizing and importing WAD files, with support for symbolic linking to save disk space.

---

## Features

- **Nightdive Folder Selection**: Set the folder where the game loads mods from (default: Nightdive's DOOM mod directory).
- **PWADs Folder Selection**: Choose a custom folder to store WADs, maps, and mods.
- **Symbolic Link Option**: Optionally create symbolic links for mods instead of copying, saving disk space.
- **Batch Import**: Import multiple WADs from a folder.
- **Console Output**: Real-time console output for user feedback and logging.
- **Mod Management**:
  - Display mods with prefixes:
    - `(SL)` for symlinked mods
    - `(CPY)` for mods both in the Nightdive and PWADs folders
    - `(ONL)` for mods only in the Nightdive folder.
  - Delete selected mods from the Nightdive folder.
- **Persistent Configuration**: Save settings like folder paths, window size, and symbolic link preference.

---

## Table of Contents
- [Installation](#installation)
  - [Windows](#windows)
  - [Linux](#linux)
- [Usage](#usage)
  - [Running the Application](#running-the-application)
  - [Mod Import Options](#mod-import-options)
  - [Symbolic Linking](#symbolic-linking)
- [Usage Tips](#usage-tips)
- [Repository Structure](#repository-structure)
- [License](#license)
- [Credits](#credits)

---

## Installation

### Windows

#### Option 1: Download the Latest Release

1. Visit the [ReNightdive Wad Manager Releases](https://github.com/Retzilience/ReNight/releases) page on GitHub.
2. Download the latest `.exe` release file.
3. Run the downloaded `.exe` to start the application.

#### Option 2: Build from Source

1. **Clone the Repository**:
    ```bash
    git clone https://github.com/Retzilience/ReNight.git
    cd ReNight
    ```

2. **Set Up a Virtual Environment**:
    ```bash
    python -m venv venv
    ```

3. **Activate the Virtual Environment**:
   ```bash
   venv\Scripts\activate
   ```

4. **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

5. **Build the Application with PyInstaller**:
    ```bash
    pyinstaller --onefile --windowed --icon=ReNight.ico --add-data "ReNight.ico;." ReNight.pyw
    ```

6. **Run the Application**:
   - The executable will be located in the `dist` folder. Run it to start the application:
     ```bash
     dist\ReNight.exe
     ```

### Linux

1. **Install Dependencies**:
   - Ensure Python 3 and `pip` are installed.
   - Install the following:
     ```bash
     sudo apt update
     sudo apt install python3 python3-pip python3-venv
     ```

2. **Clone the Repository**:
    ```bash
    git clone https://github.com/Retzilience/ReNight.git
    cd ReNight
    ```

3. **Set Up a Virtual Environment**:
    ```bash
    python3 -m venv venv
    ```

4. **Activate the Virtual Environment**:
    ```bash
    source venv/bin/activate
    ```

5. **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

6. **Build the Application with PyInstaller**:
    ```bash
    pyinstaller --onefile --windowed --icon=ReNight.ico --add-data "ReNight.ico:." ReNight.pyw
    ```

7. **Run the Application**:
   - The executable will be located in the `dist` folder. Run it to start the application:
     ```bash
     ./dist/ReNight
     ```

---

## Usage

### Running the Application

After launching, the main window will provide options to select folders, import WADs, and view current mods in the Nightdive folder.

### Mod Import Options

- **Pick WAD**: Allows you to select one or multiple WAD files to import.
- **Pick Folder (Batch)**: Select a folder containing multiple WAD files to import them all at once.
- **Symbolic Link Option**: When checked, WADs are imported as symbolic links rather than copied to the Nightdive Folder.

### Symbolic Linking

- Enabling this option saves disk space by creating a symbolic link to the file in the Nightdive Folder.
- Note: Symbolic links may not work on all systems or configurations, so use this option as needed.

---

## Usage Tips

1. **Set Your PWADs Folder**: Setting this first allows for accurate detection of copied mods.
2. **Switch Between Copy and Link Modes**: To change a mod from `(SL)` to `(CPY)` or vice versa, simply re-import it with the desired option.
3. **Config Persistence**: Your folder settings, window size, and symbolic link preferences are saved in `config.json`, so they persist between sessions.
4. **Limitations**:
   - The application can only load single-WAD mods directly through the Nightdive source port's in-game UI.
   - `.pk3` files, UDMF, and GZDoom mods are incompatible with the KEX sourceport.

---

## Repository Structure

After building, your repository will look like this:

```
C:\Users\retzilience\ReNight
│
├── build/                 # Temporary build files created by PyInstaller
├── dist/                  # Final output directory with the executable
│   └── ReNight.exe        # The compiled single-file executable
├── venv/                  # Virtual environment directory (not included in version control)
├── ReNight.ico            # Icon file for the application
├── ReNight.pyw            # Main Python script
├── ReNight.spec           # PyInstaller specification file
└── requirements.txt       # Lists all required Python libraries
```

---

## License

This project is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License. For more details, visit [CC BY-NC-SA 4.0](http://creativecommons.org/licenses/by-nc-sa/4.0/).

---

## Credits

Made with love, rip and tear by **retzilience**, 2024.

---

For updates, see the [GitHub Repository](https://github.com/Retzilience/ReNight).
