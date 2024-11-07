import os
import sys
import json
import shutil
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QCheckBox, QListWidget, QTextBrowser, QDialog, QScrollArea
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

CONFIG_FILE = 'config.json'

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def get_app_directory():
    """Get the directory where the executable or script is located."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

class ReNight(QWidget):
    def __init__(self):
        super().__init__()

        self.version = "0.02"

        self.setWindowTitle(f"ReNight-{self.version}")
        icon_path = self.get_icon_path()
        print(f"Icon path resolved to: {icon_path}")
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
            self.setWindowIcon(app_icon)
        else:
            print(f"Icon file not found at {icon_path}. Please ensure the icon file is placed correctly.")

        self.resize(800, 600)

        self.selected_files = []

        self.load_config()

        main_layout = QHBoxLayout()
        input_layout = QVBoxLayout()
        mod_list_layout = QVBoxLayout()

        # Nightdive Folder
        self.nightdive_folder_label = QLabel("Nightdive Folder:")
        self.nightdive_folder_input = QLineEdit(self.nightdive_folder)
        self.nightdive_folder_button = QPushButton("Browse")
        self.nightdive_folder_button.clicked.connect(self.select_nightdive_folder)
        input_layout.addWidget(self.nightdive_folder_label)
        input_layout.addWidget(self.nightdive_folder_input)
        input_layout.addWidget(self.nightdive_folder_button)

        # PWADs Folder
        self.pwad_folder_label = QLabel("PWADs Folder:")
        self.pwad_folder_input = QLineEdit(self.pwad_folder)
        self.pwad_folder_button = QPushButton("Browse")
        self.pwad_folder_button.clicked.connect(self.select_pwad_folder)
        input_layout.addWidget(self.pwad_folder_label)
        input_layout.addWidget(self.pwad_folder_input)
        input_layout.addWidget(self.pwad_folder_button)

        # Symlink Option
        self.symlink_checkbox = QCheckBox("Create as .symlink")
        self.symlink_checkbox.setChecked(self.symlink_option)
        self.symlink_checkbox.stateChanged.connect(self.save_config)
        input_layout.addWidget(self.symlink_checkbox)

        # Pick WAD and Batch Buttons
        self.pick_wad_button = QPushButton("Pick WAD")
        self.pick_wad_button.clicked.connect(self.pick_wad)
        self.pick_folder_button = QPushButton("Pick Folder (Batch)")
        self.pick_folder_button.clicked.connect(self.pick_folder)
        input_layout.addWidget(self.pick_wad_button)
        input_layout.addWidget(self.pick_folder_button)

        input_layout.addSpacing(10)

        # Import Button
        self.import_button = QPushButton("Import")
        self.import_button.clicked.connect(self.import_mod)
        input_layout.addWidget(self.import_button)

        # Console Output
        self.console_output = QTextBrowser()
        self.console_output.setOpenExternalLinks(False)
        self.console_output.setReadOnly(True)
        self.console_output.setHtml(
            f"<p>Welcome to <b>ReNightdive Wad Manager</b> v{self.version}</p>"
            "<li>Made with love, rip and tear by retzilience</li>"
            "<li>CC BY-NC-SA 4.0, 2024</p>"
            "<p>Check 'Help' for assistance, links, and more.</p><br>"
        )
        input_layout.addWidget(QLabel("Console Output:"))
        input_layout.addWidget(self.console_output)

        # Mod List
        self.mod_list_label = QLabel("Mods in Nightdive Folder:")
        self.mod_list = QListWidget()
        self.mod_list.setSelectionMode(QListWidget.ExtendedSelection)
        mod_list_layout.addWidget(self.mod_list_label)
        mod_list_layout.addWidget(self.mod_list)

        # Delete and Help Buttons
        self.delete_button = QPushButton("Delete Selected Mod(s)")
        self.delete_button.clicked.connect(self.delete_mod)
        mod_list_layout.addWidget(self.delete_button)

        self.help_button = QPushButton("Help")
        self.help_button.clicked.connect(self.show_help)
        mod_list_layout.addWidget(self.help_button)

        main_layout.addLayout(input_layout)
        main_layout.addLayout(mod_list_layout)
        self.setLayout(main_layout)

        # Update mod list when folders change
        self.nightdive_folder_input.editingFinished.connect(self.on_nightdive_folder_changed)
        self.pwad_folder_input.editingFinished.connect(self.on_pwad_folder_changed)

        self.load_mod_list()

    def get_icon_path(self):
        return resource_path('ReNight.ico')

    def load_config(self):
        self.nightdive_folder = os.path.normpath(self.get_default_nightdive_folder())
        self.pwad_folder = ''
        self.symlink_option = True

        app_dir = get_app_directory()
        config_path = os.path.join(app_dir, CONFIG_FILE)
        print(f"Config path: {config_path}")

        if os.path.isfile(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.nightdive_folder = os.path.normpath(config.get('nightdive_folder', self.nightdive_folder))
                    self.pwad_folder = os.path.normpath(config.get('pwad_folder', self.pwad_folder))
                    self.symlink_option = config.get('symlink_option', self.symlink_option)
                    window_size = config.get('window_size', {})
                    if window_size:
                        self.resize(window_size.get('width', 800), window_size.get('height', 600))
            except Exception as e:
                print(f"Error loading config: {e}")

    def save_config(self):
        config = {
            'nightdive_folder': os.path.normpath(self.nightdive_folder_input.text()),
            'pwad_folder': os.path.normpath(self.pwad_folder_input.text()),
            'symlink_option': self.symlink_checkbox.isChecked(),
            'window_size': {
                'width': self.size().width(),
                'height': self.size().height()
            }
        }
        app_dir = get_app_directory()
        config_path = os.path.join(app_dir, CONFIG_FILE)
        print(f"Saving config to: {config_path}")
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get_default_nightdive_folder(self):
        user_home = os.path.expanduser("~")
        default_path = os.path.join(user_home, 'Saved Games', 'Nightdive Studios', 'DOOM')
        return default_path

    def select_nightdive_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Nightdive Folder")
        if folder:
            self.nightdive_folder_input.setText(os.path.normpath(folder))
            self.nightdive_folder = os.path.normpath(folder)
            self.save_config()
            self.load_mod_list()

    def select_pwad_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select PWADs Folder")
        if folder:
            self.pwad_folder_input.setText(os.path.normpath(folder))
            self.pwad_folder = os.path.normpath(folder)
            self.save_config()
            self.load_mod_list()

    def on_nightdive_folder_changed(self):
        self.nightdive_folder = os.path.normpath(self.nightdive_folder_input.text())
        self.save_config()
        self.load_mod_list()

    def on_pwad_folder_changed(self):
        self.pwad_folder = os.path.normpath(self.pwad_folder_input.text())
        self.save_config()
        self.load_mod_list()

    def pick_wad(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select WAD File(s)", self.pwad_folder_input.text(), "WAD Files (*.wad)"
        )
        if files:
            self.selected_files = files
            self.console_output.append(f"Selected WAD file(s): {', '.join(files)}")

    def pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder for Batch Import")
        if folder:
            self.selected_files = [
                os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".wad")
            ]
            self.console_output.append(f"Selected batch WAD files from folder: {folder}")

    def import_mod(self):
        if not self.selected_files:
            self.console_output.append("No files selected for import.")
            return

        target_folder = self.nightdive_folder_input.text()

        for wad_path in self.selected_files:
            link_name = os.path.join(target_folder, os.path.basename(wad_path))
            try:
                if self.symlink_checkbox.isChecked():
                    if os.path.exists(link_name):
                        os.unlink(link_name)
                    os.symlink(wad_path, link_name)
                    self.console_output.append(f"Created symlink for: {link_name}")
                else:
                    if os.path.exists(link_name):
                        os.unlink(link_name)
                    shutil.copyfile(wad_path, link_name)
                    self.console_output.append(f"Copied file to: {link_name}")
            except OSError as e:
                self.console_output.append(f"Error processing {wad_path}: {e}")

        self.load_mod_list()
        self.selected_files = []

    def load_mod_list(self):
        self.mod_list.clear()
        target_folder = self.nightdive_folder_input.text()
        pwad_folder = self.pwad_folder_input.text()

        if os.path.isdir(target_folder):
            for item in os.listdir(target_folder):
                full_path = os.path.join(target_folder, item)

                if item.lower().endswith(".wad") or os.path.islink(full_path):
                    if os.path.islink(full_path):
                        prefix = "(SL)"
                    elif pwad_folder and os.path.exists(os.path.join(pwad_folder, item)):
                        prefix = "(CPY)"
                    else:
                        prefix = "(ONL)"

                    self.mod_list.addItem(f"{prefix} {item}")

    def delete_mod(self):
        selected_items = self.mod_list.selectedItems()
        if not selected_items:
            self.console_output.append("No mod selected to delete.")
            return

        target_folder = self.nightdive_folder_input.text()
        for item in selected_items:
            full_item_text = item.text()
            parts = full_item_text.split(' ', 1)
            if len(parts) < 2:
                self.console_output.append(f"Invalid item format: {full_item_text}")
                continue
            mod_name = parts[1].strip()
            full_path = os.path.join(target_folder, mod_name)
            print(f"Attempting to delete: {full_path}")
            try:
                if os.path.exists(full_path):
                    os.unlink(full_path)
                    self.console_output.append(f"Deleted mod: {full_path}")
                else:
                    self.console_output.append(f"Mod not found: {full_path}")
            except OSError as e:
                self.console_output.append(f"Error deleting {full_path}: {e}")

        self.load_mod_list()

    def show_help(self):
        help_text = (
            f"<h2>ReNightdive Local Wad Manager (v{self.version})</h2>"
            "<p>This application helps you manage your local DOOM WADs with ease for the Nightdive 'DOOM + DOOM II' KEX 2024 source port. Imported WADs will be available in the in-game local mod list.</p>"
            "<h3>Features:</h3>"
            "<ul>"
            "<li><b>Nightdive Folder:</b> The folder where the game loads mods from. By default, the program sets it to your mod directory for Nightdive's DOOM. You can change it if needed.</li>"
            "<li><b>PWADs Folder:</b> The folder where your custom WADs, maps, and mods are stored. This is left empty by default for you to set.</li>"
            "<li><b>Create as .symlink:</b> When checked, the program creates symbolic links to your mods instead of copying them. This saves disk space but may require additional permissions or settings on some systems. If unchecked, mods will be copied to the Nightdive Folder.</li>"
            "<li><b>Pick WAD:</b> Select one or multiple WAD files to import.</li>"
            "<li><b>Pick Folder (Batch):</b> Select a folder containing multiple WAD files to import all at once.</li>"
            "<li><b>Import:</b> After selecting mods, click this button to process the import based on your settings.</li>"
            "<li><b>Mod List:</b> Displays the mods currently in your Nightdive Folder with the following labels:</li>"
            "<ul>"
            "<li><b>(SL):</b> Symlinked mod.</li>"
            "<li><b>(CPY):</b> Mod copied to Nightdive Folder and also present in PWADs Folder.</li>"
            "<li><b>(ONL):</b> Mod only present in Nightdive Folder.</li>"
            "</ul>"
            "<li><b>Delete Selected Mod(s):</b> Deletes the selected mod(s) from the Nightdive Folder.</li>"
            "</ul>"
            "<h3>Usage Tips:</h3>"
            "<ul>"
            "<li>Select your PWADs Folder first to enable proper detection of copied mods.</li>"
            "<li>If you want to change a mod from one copy mode to another (e.g., (SL) to (CPY)), simply import it again with the desired format.</li>"
            "<li>The application saves your settings between sessions in a config.json file in the executable's directory.</li>"
            "<li>Due to how the game WAD loader works, you can only load single-WAD mods through the in-game UI. Multi-WAD mods need to be loaded with launch parameters.</li>"
            "<li>.pk3, UDMF WADs, or 'ZDoom mods' do NOT work on the KEX source port; this tool won't change that.</li>"
            "</ul>"
            "<h3>Credits:</h3>"
            "<p>Made with love, rip and tear by <span style='font-weight: bold; font-size: 1.1em; letter-spacing: 0.5px;'>retzilience</span></p>"
            "<li>Huge thanks to <span style='font-weight: bold; font-size: 1.1em; letter-spacing: 0.5px;'>RataUnderground</span> for the app logo!</li>"
            "<li>License: CC BY-NC-SA 4.0, 2024</li>"
            "<li>Check for updates at: <a href='https://github.com/Retzilience/ReNight'>GitHub Repository Link</a><li>"
        )
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Help")
        icon_path = self.get_icon_path()
        if os.path.exists(icon_path):
            help_dialog.setWindowIcon(QIcon(icon_path))

        help_layout = QVBoxLayout()
        help_label = QLabel(help_text)
        help_label.setWordWrap(True)
        help_label.setOpenExternalLinks(True)

        help_dialog.resize(700, 720)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.addWidget(help_label)
        scroll_area.setWidget(scroll_content)

        help_layout.addWidget(scroll_area)
        help_dialog.setLayout(help_layout)
        help_dialog.exec()

    def closeEvent(self, event):
        self.save_config()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    icon_path = resource_path('ReNight.ico')
    print(f"Executable icon path resolved to: {icon_path}")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    else:
        print(f"Icon file not found at {icon_path}. Please ensure the icon file is placed correctly.")

    loader = ReNight()
    loader.show()
    sys.exit(app.exec())
