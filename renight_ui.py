# renight_ui.py
# Refactor: remove embedded urllib/zip/tar update implementation; delegate to renight_updater.UpdateClient.

from __future__ import annotations

import os
import sys
import time
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer, QFileSystemWatcher, QUrl
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

import resources_rc  # noqa: F401

from renight_core import VERSION, UPDATE_INFO_URL
from renight_help import HELP_HTML
from renight_model import ReNightModel
from renight_updater import UpdateClient, get_os_tag


class ReNightWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.model = ReNightModel()
        self.version = VERSION

        self.setWindowTitle(f"ReNight-{self.version}")
        self.setWindowIcon(QIcon(":/icons/ReNight.ico"))
        self.resize(800, 600)

        self.selected_files: List[str] = []
        self.help_update_button: Optional[QPushButton] = None

        self.fs_watcher = QFileSystemWatcher(self)
        self.fs_watch_debounce = QTimer(self)
        self.fs_watch_debounce.setSingleShot(True)
        self.fs_watch_debounce.timeout.connect(self.refresh_mod_list)
        self.fs_watcher.directoryChanged.connect(self.on_fs_changed)
        self.fs_watcher.fileChanged.connect(self.on_fs_changed)

        main_layout = QHBoxLayout()
        input_layout = QVBoxLayout()
        mod_list_layout = QVBoxLayout()

        self.nightdive_folder_label = QLabel("Nightdive Folder:")
        self.nightdive_folder_input = QLineEdit(self.model.nightdive_folder)
        self.nightdive_folder_button = QPushButton("Browse")
        self.nightdive_folder_button.clicked.connect(self.select_nightdive_folder)
        input_layout.addWidget(self.nightdive_folder_label)
        input_layout.addWidget(self.nightdive_folder_input)
        input_layout.addWidget(self.nightdive_folder_button)

        self.pwad_folder_label = QLabel("PWADs Folder:")
        self.pwad_folder_input = QLineEdit(self.model.pwad_folder)
        self.pwad_folder_button = QPushButton("Browse")
        self.pwad_folder_button.clicked.connect(self.select_pwad_folder)
        input_layout.addWidget(self.pwad_folder_label)
        input_layout.addWidget(self.pwad_folder_input)
        input_layout.addWidget(self.pwad_folder_button)

        self.symlink_checkbox = QCheckBox("Create as .symlink")
        self.symlink_checkbox.setChecked(self.model.symlink_option)
        self.symlink_checkbox.stateChanged.connect(self.on_symlink_option_changed)
        input_layout.addWidget(self.symlink_checkbox)

        self.pick_wad_button = QPushButton("Pick WAD")
        self.pick_wad_button.clicked.connect(self.pick_wad)
        self.pick_folder_button = QPushButton("Pick Folder (Batch)")
        self.pick_folder_button.clicked.connect(self.pick_folder)
        input_layout.addWidget(self.pick_wad_button)
        input_layout.addWidget(self.pick_folder_button)
        input_layout.addSpacing(10)

        self.import_button = QPushButton("Import")
        self.import_button.clicked.connect(self.import_mod)
        input_layout.addWidget(self.import_button)

        self.console_output = QTextBrowser()
        self.console_output.setOpenExternalLinks(False)
        self.console_output.setReadOnly(True)
        self.console_output.setHtml(
            f"<p>Welcome to <b>ReNight Wad Manager</b> v{self.version}</p>"
            "<li>Made with love, rip and tear by retzilience</li>"
            "<li>CC BY-NC-SA 4.0, 2024</p>"
            "<p>Check 'Help' for assistance, links, and more.</p><br>"
        )
        input_layout.addWidget(QLabel("Console Output:"))
        input_layout.addWidget(self.console_output)

        self.mod_list_label = QLabel("Mods in Nightdive Folder:")
        self.mod_table = QTableWidget(0, 2)
        self.mod_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.mod_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.mod_table.setShowGrid(False)
        self.mod_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.mod_table.horizontalHeader().setVisible(False)
        self.mod_table.verticalHeader().setVisible(False)

        header = self.mod_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)

        self.mod_table.setStyleSheet(
            "QTableWidget { border: none; }"
            "QTableWidget::item { padding-left: 8px; padding-right: 8px; }"
        )

        mod_list_layout.addWidget(self.mod_list_label)
        mod_list_layout.addWidget(self.mod_table)

        self.delete_button = QPushButton("Delete Selected Mod(s)")
        self.delete_button.clicked.connect(self.delete_mod)
        mod_list_layout.addWidget(self.delete_button)

        self.help_button = QPushButton("Help")
        self.help_button.clicked.connect(self.show_help)
        mod_list_layout.addWidget(self.help_button)

        main_layout.addLayout(input_layout)
        main_layout.addLayout(mod_list_layout)
        self.setLayout(main_layout)

        self.nightdive_folder_input.editingFinished.connect(self.on_nightdive_folder_changed)
        self.pwad_folder_input.editingFinished.connect(self.on_pwad_folder_changed)

        self.set_import_button_idle()
        self.refresh_mod_list()
        self.update_watch_paths()

        self._update_client = UpdateClient(
            parent_widget=self,
            app_version=self.version,
            descriptor_url=UPDATE_INFO_URL,
            os_tag=get_os_tag(),
            get_skip_version=lambda: getattr(self.model, "snoozed_version", "") or "",
            set_skip_version=self._set_snoozed_version,
            record_check_timestamp=self._record_update_check_timestamp,
        )

        QTimer.singleShot(2000, self._run_silent_update_check)

    # ----- update persistence -----

    def _record_update_check_timestamp(self) -> None:
        try:
            self.model.last_update_check = time.time()
            self.model._save_config()
        except Exception:
            return

    def _set_snoozed_version(self, version: str) -> None:
        try:
            self.model.snoozed_version = str(version)
            self.model._save_config()
        except Exception:
            return

    # ----- import button states -----

    def set_import_button_idle(self) -> None:
        self.import_button.setEnabled(False)
        self.import_button.setText("Import")
        self.import_button.setStyleSheet("")

    def set_import_button_ready(self, label: str) -> None:
        self.import_button.setEnabled(True)
        self.import_button.setText(f"Import: {label}")
        self.import_button.setStyleSheet(
            "QPushButton { background-color: #d9a441; color: black; }"
        )

    def set_import_button_result(self, success: bool) -> None:
        if success:
            self.import_button.setEnabled(False)
            self.import_button.setText("Imported")
            self.import_button.setStyleSheet(
                "QPushButton { background-color: #2d5f3b; color: white; }"
            )
        else:
            self.import_button.setEnabled(False)
            self.import_button.setText("Failed!")
            self.import_button.setStyleSheet(
                "QPushButton { background-color: #a33a3a; color: white; }"
            )

        QTimer.singleShot(1000, self.set_import_button_idle)

    # ----- filesystem watching -----

    def update_watch_paths(self) -> None:
        old_paths = self.fs_watcher.directories() + self.fs_watcher.files()
        if old_paths:
            self.fs_watcher.removePaths(old_paths)

        paths: List[str] = []
        nd = self.model.nightdive_folder
        if os.path.isdir(nd):
            paths.append(nd)

        pw = self.model.pwad_folder
        if os.path.isdir(pw):
            for root, _, _ in os.walk(pw):
                paths.append(root)

        if paths:
            self.fs_watcher.addPaths(paths)

    def on_fs_changed(self, _path: str) -> None:
        if not self.fs_watch_debounce.isActive():
            self.fs_watch_debounce.start(300)

    # ----- callbacks: config changes -----

    def on_symlink_option_changed(self, state: int) -> None:
        self.model.set_symlink_option(bool(state))

    def on_nightdive_folder_changed(self) -> None:
        path = os.path.normpath(self.nightdive_folder_input.text())
        self.model.set_nightdive_folder(path)
        self.selected_files = []
        self.set_import_button_idle()
        self.refresh_mod_list()
        self.update_watch_paths()

    def on_pwad_folder_changed(self) -> None:
        path = os.path.normpath(self.pwad_folder_input.text())
        self.model.set_pwad_folder(path)
        self.selected_files = []
        self.set_import_button_idle()
        self.refresh_mod_list()
        self.update_watch_paths()

    def select_nightdive_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Nightdive Folder")
        if folder:
            folder = os.path.normpath(folder)
            self.nightdive_folder_input.setText(folder)
            self.model.set_nightdive_folder(folder)
            self.selected_files = []
            self.set_import_button_idle()
            self.refresh_mod_list()
            self.update_watch_paths()

    def select_pwad_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select PWADs Folder")
        if folder:
            folder = os.path.normpath(folder)
            self.pwad_folder_input.setText(folder)
            self.model.set_pwad_folder(folder)
            self.selected_files = []
            self.set_import_button_idle()
            self.refresh_mod_list()
            self.update_watch_paths()

    # ----- selection -----

    def pick_wad(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select WAD File(s)",
            self.pwad_folder_input.text(),
            "WAD Files (*.wad)",
        )
        if files:
            self.selected_files = files
            self.console_output.append(f"Selected WAD file(s): {', '.join(files)}")
            if len(files) == 1:
                label = f"{os.path.basename(files[0])} (WAD)"
            else:
                label = f"{os.path.basename(files[0])} (+{len(files) - 1} more)"
            self.set_import_button_ready(label)
        else:
            self.selected_files = []
            self.set_import_button_idle()

    def pick_folder(self) -> None:
        start_dir = self.pwad_folder_input.text().strip()
        if not start_dir or not os.path.isdir(start_dir):
            start_dir = os.path.expanduser("~")

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder for Batch Import",
            start_dir,
        )
        if folder:
            folder = os.path.normpath(folder)
            self.selected_files = [
                os.path.join(folder, f)
                for f in os.listdir(folder)
                if f.lower().endswith(".wad")
            ]
            self.console_output.append(f"Selected batch WAD files from folder: {folder}")
            label = f"{os.path.basename(folder)} (Folder)"
            self.set_import_button_ready(label)
        else:
            self.selected_files = []
            self.set_import_button_idle()

    # ----- import -----

    def import_mod(self) -> None:
        any_success, any_failure, messages = self.model.import_mods(self.selected_files)
        for msg in messages:
            self.console_output.append(msg)

        self.selected_files = []
        self.refresh_mod_list()
        self.update_watch_paths()
        self.set_import_button_result(success=any_success and not any_failure)

    # ----- list -----

    def refresh_mod_list(self) -> None:
        self.mod_table.setRowCount(0)
        entries = self.model.scan_mods()
        for row, (prefix, name) in enumerate(entries):
            self.mod_table.insertRow(row)
            name_item = QTableWidgetItem(name)
            name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            prefix_item = QTableWidgetItem(prefix)
            prefix_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.mod_table.setItem(row, 0, name_item)
            self.mod_table.setItem(row, 1, prefix_item)

    # ----- delete -----

    def delete_mod(self) -> None:
        selection = self.mod_table.selectionModel().selectedRows()
        if not selection:
            self.console_output.append("No mod selected to delete.")
            return

        items_info: List[tuple[str, str]] = []
        has_onl = False

        for index in selection:
            row = index.row()
            name_item = self.mod_table.item(row, 0)
            prefix_item = self.mod_table.item(row, 1)
            if name_item is None:
                continue
            prefix = prefix_item.text() if prefix_item is not None else ""
            mod_name = name_item.text().strip()
            if prefix == "(ONL)":
                has_onl = True
            items_info.append((prefix, mod_name))

        if not items_info:
            return

        if has_onl:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Delete ONL mod")
            msg.setText(
                "This file is present only on the Nightdive folder, are you sure you want to delete?"
            )
            delete_button = msg.addButton("Delete", QMessageBox.AcceptRole)
            msg.addButton("Keep", QMessageBox.RejectRole)
            msg.exec()
            if msg.clickedButton() is not delete_button:
                return

        names = [name for _, name in items_info]
        messages = self.model.delete_mods(names)
        for msg in messages:
            self.console_output.append(msg)
        self.refresh_mod_list()

    # ----- updates -----

    def _run_silent_update_check(self) -> None:
        now = time.time()
        interval = 6 * 60 * 60
        last = getattr(self.model, "last_update_check", 0.0)
        if last and now - last < interval:
            return

        self._update_client.check_now(ignore_skip=False, result_callback=None)

    def _flash_update_button(self, button: QPushButton, text: str) -> None:
        if button is None:
            return

        def restore() -> None:
            button.setEnabled(True)
            button.setText("Check for updates")
            button.setStyleSheet("")

        button.setEnabled(False)
        button.setText(text)
        button.setStyleSheet("QPushButton { background-color: #a33a3a; color: white; }")
        QTimer.singleShot(2000, restore)

    def _on_manual_update_result(self, result: str, button: Optional[QPushButton]) -> None:
        if result == "no_update":
            self.console_output.append("No new ReNight updates available.")
            if button is not None:
                button.setEnabled(True)
                button.setText("Check for updates")
                button.setStyleSheet("")
        elif result == "error":
            self.console_output.append("Update check failed.")
            if button is not None:
                self._flash_update_button(button, "Failed to check")
        else:
            if button is not None:
                button.setEnabled(True)
                button.setText("Check for updates")
                button.setStyleSheet("")

    # ----- help -----

    def show_help(self) -> None:
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Help")
        help_dialog.setWindowIcon(QIcon(":/icons/ReNight.ico"))

        help_layout = QVBoxLayout()
        help_label = QLabel(HELP_HTML)
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

        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 8, 0, 0)

        self.help_update_button = QPushButton("Check for updates")
        self.help_update_button.clicked.connect(self.on_help_check_updates)

        report_button = QPushButton("Report a bug")
        report_button.clicked.connect(self.on_help_report_bug)

        buttons_layout.addWidget(self.help_update_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(report_button)

        help_layout.addLayout(buttons_layout)

        help_dialog.setLayout(help_layout)
        help_dialog.exec()

    def on_help_check_updates(self) -> None:
        button = self.help_update_button
        if button is not None:
            button.setEnabled(False)
            button.setText("Checking...")
            button.setStyleSheet("QPushButton { background-color: #d9a441; color: black; }")

        def cb(result: str) -> None:
            self._on_manual_update_result(result, button)

        self._update_client.check_now(ignore_skip=True, result_callback=cb)

    def on_help_report_bug(self) -> None:
        QDesktopServices.openUrl(QUrl("https://github.com/Retzilience/ReNight/issues"))

    # ----- Qt events -----

    def focusInEvent(self, event) -> None:  # type: ignore[override]
        self.refresh_mod_list()
        super().focusInEvent(event)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        event.accept()
