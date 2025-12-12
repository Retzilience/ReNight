# renight_updater.py
# Qt-side update helper: async descriptor fetch + optional/mandatory dialogs + async staging.

from __future__ import annotations

import os
import shutil
import sys
import time
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from PySide6.QtCore import QObject, QTimer, QUrl, Qt, QThread, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QApplication, QCheckBox, QMessageBox, QWidget

from renight_core import UPDATE_INFO_URL, compare_versions, get_data_directory
from renight_state import load_config_dict, save_config_dict
from renight_utils import open_url_external


DEFAULT_RELEASES_URL = "https://github.com/Retzilience/ReNight/releases/latest"


@dataclass(frozen=True)
class UpdateEntry:
    version: str
    flags: tuple[str, ...]
    url: str


def get_os_tag() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "darwin":
        return "macos"
    return ""


def _parse_descriptor(
    text: str,
    os_tag: str,
    current_version: str,
) -> Tuple[Optional[UpdateEntry], Optional[UpdateEntry]]:
    """
    Backward-compatible descriptor parser.

    Preferred format (SoundBoard27-style):
        version | os | flags,flags,... | download_url

    Compatibility:
        If a line has >4 parts, the first 4 are treated as above and extra parts are ignored.
        If a line has exactly 3 parts, it is treated as: version|os|url with empty flags.
    """
    latest: Optional[UpdateEntry] = None
    current: Optional[UpdateEntry] = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue

        version_str = parts[0]
        os_name = parts[1]
        if os_name.lower() != os_tag.lower():
            continue

        if len(parts) == 3:
            flags_str = ""
            url = parts[2]
        else:
            flags_str = parts[2]
            url = parts[3] if len(parts) >= 4 else ""

        flags = tuple(f.strip().lower() for f in flags_str.split(",") if f.strip())
        entry = UpdateEntry(version=version_str, flags=flags, url=url)

        if latest is None or compare_versions(entry.version, latest.version) > 0:
            latest = entry

        if compare_versions(entry.version, current_version) == 0:
            current = entry

    return latest, current


def _get_updates_dir() -> str:
    return os.path.join(get_data_directory(), "updates")


def _find_staged_executable(stage_dir: str) -> Optional[str]:
    candidates: list[str] = []

    if sys.platform.startswith("win"):
        for root, _, files in os.walk(stage_dir):
            for name in files:
                if not name.lower().endswith(".exe"):
                    continue
                candidates.append(os.path.join(root, name))
        if not candidates:
            return None
        for path in candidates:
            if os.path.basename(path).lower() == "renight.exe":
                return path
        return candidates[0]

    for root, _, files in os.walk(stage_dir):
        for name in files:
            path = os.path.join(root, name)
            try:
                st = os.stat(path)
            except OSError:
                continue
            if not os.path.isdir(path) and (st.st_mode & 0o111):
                candidates.append(path)

    if not candidates:
        return None

    for path in candidates:
        if os.path.basename(path) == "ReNight":
            return path
    return candidates[0]


class _ExtractorWorker(QObject):
    finished = Signal(bool, str, str)  # ok, message, staged_exe

    def __init__(self, archive_path: str, stage_dir: str) -> None:
        super().__init__()
        self._archive_path = archive_path
        self._stage_dir = stage_dir

    def run(self) -> None:
        import tarfile
        import zipfile

        lower = self._archive_path.lower()
        try:
            os.makedirs(self._stage_dir, exist_ok=True)

            if lower.endswith(".zip"):
                with zipfile.ZipFile(self._archive_path, "r") as zf:
                    zf.extractall(self._stage_dir)
            elif (
                lower.endswith(".tar.gz")
                or lower.endswith(".tgz")
                or lower.endswith(".tar.bz2")
                or lower.endswith(".tar")
            ):
                with tarfile.open(self._archive_path, "r:*") as tf:
                    tf.extractall(self._stage_dir)
            else:
                self.finished.emit(False, "Unsupported archive format.", "")
                return

            staged = _find_staged_executable(self._stage_dir)
            if not staged:
                self.finished.emit(False, "Could not locate ReNight binary in extracted update.", "")
                return

            self.finished.emit(True, "Extracted update.", staged)
        except Exception as e:
            self.finished.emit(False, f"Extraction failed: {e}", "")


class UpdateClient(QObject):
    """
    Async update helper with:
      - descriptor fetch via QNetworkAccessManager
      - in-flight guard
      - explicit timeouts
      - skip/snooze handling via callbacks
      - optional/mandatory dialogs
      - optional self-update staging for frozen builds
    """

    def __init__(
        self,
        parent_widget: QWidget,
        app_version: str,
        descriptor_url: str = UPDATE_INFO_URL,
        os_tag: Optional[str] = None,
        get_skip_version: Optional[Callable[[], str]] = None,
        set_skip_version: Optional[Callable[[str], None]] = None,
        record_check_timestamp: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent_widget)

        self._parent_widget = parent_widget
        self._app_version = str(app_version).strip()
        self._descriptor_url = descriptor_url
        self._os_tag = (os_tag or get_os_tag()).strip()

        self._get_skip_version = get_skip_version or (lambda: "")
        self._set_skip_version = set_skip_version or (lambda _v: None)
        self._record_check_timestamp = record_check_timestamp or (lambda: None)

        self._manager = QNetworkAccessManager(self)
        self._manager.finished.connect(self._on_descriptor_reply)

        self._in_flight = False
        self._ignore_skip_for_this_request = False
        self._result_callback_for_this_request: Optional[Callable[[str], None]] = None

    def check_now(
        self,
        ignore_skip: bool,
        result_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._request_descriptor(ignore_skip=ignore_skip, result_callback=result_callback)

    def _request_descriptor(
        self,
        ignore_skip: bool,
        result_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        if not self._os_tag:
            self._notify_result("error", result_callback)
            return

        if self._in_flight:
            self._notify_result("error", result_callback)
            return

        self._in_flight = True
        self._ignore_skip_for_this_request = ignore_skip
        self._result_callback_for_this_request = result_callback

        req = QNetworkRequest(QUrl(self._descriptor_url))
        reply = self._manager.get(req)

        timer = QTimer(self)
        timer.setSingleShot(True)

        def on_timeout() -> None:
            try:
                if reply.isRunning():
                    reply.abort()
            except Exception:
                pass

        def cleanup() -> None:
            try:
                timer.stop()
                timer.deleteLater()
            except Exception:
                pass

        timer.timeout.connect(on_timeout)
        reply.finished.connect(cleanup)
        timer.start(8000)

    def _on_descriptor_reply(self, reply: QNetworkReply) -> None:
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self._finalize_descriptor_result("error", None, None, "")
                return

            data = reply.readAll()
            try:
                text = bytes(data).decode("utf-8", errors="replace")
            except Exception:
                self._finalize_descriptor_result("error", None, None, "")
                return

            latest, current = _parse_descriptor(text, self._os_tag, self._app_version)
            self._finalize_descriptor_result("ok", latest, current, text)
        finally:
            self._in_flight = False
            reply.deleteLater()

    def _finalize_descriptor_result(
        self,
        status: str,
        latest: Optional[UpdateEntry],
        current: Optional[UpdateEntry],
        raw_text: str,
    ) -> None:
        try:
            self._record_check_timestamp()
        except Exception:
            pass

        if status != "ok" or latest is None:
            self._notify_request_result("error")
            return

        current_is_deprecated = current is not None and ("deprecated" in current.flags)
        if current_is_deprecated:
            self._show_mandatory_dialog(latest)
            self._notify_request_result("deprecated")
            return

        if compare_versions(latest.version, self._app_version) <= 0:
            self._notify_request_result("no_update")
            return

        if not self._ignore_skip_for_this_request:
            try:
                skip = (self._get_skip_version() or "").strip()
            except Exception:
                skip = ""
            if skip and skip == latest.version:
                self._notify_request_result("no_update")
                return

        self._show_optional_dialog(latest)
        self._notify_request_result("update_available")

    def _notify_result(self, result: str, cb: Optional[Callable[[str], None]]) -> None:
        if cb is None:
            return
        try:
            cb(result)
        except Exception:
            return

    def _notify_request_result(self, result: str) -> None:
        cb = self._result_callback_for_this_request
        self._result_callback_for_this_request = None
        self._notify_result(result, cb)

    def _effective_parent(self) -> QWidget:
        w = QApplication.activeWindow()
        return w if w is not None else self._parent_widget

    def _show_optional_dialog(self, latest: UpdateEntry) -> None:
        box = QMessageBox(self._effective_parent())
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle("ReNight update available")
        box.setText(
            f"A new ReNight version {latest.version} is available.\n"
            f"You are currently running {self._app_version}."
        )

        snooze = QCheckBox("Do not remind me again for this version", box)
        box.setCheckBox(snooze)

        update_btn = box.addButton("Update now", QMessageBox.AcceptRole)
        releases_btn = box.addButton("Releases", QMessageBox.NoRole)
        later_btn = box.addButton("Later", QMessageBox.RejectRole)
        box.setDefaultButton(update_btn)

        box.setWindowModality(Qt.ApplicationModal)
        box.exec()

        clicked = box.clickedButton()

        if clicked is later_btn:
            if snooze.isChecked():
                try:
                    self._set_skip_version(latest.version)
                except Exception:
                    pass
            return

        if clicked is releases_btn:
            open_url_external(DEFAULT_RELEASES_URL)
            if snooze.isChecked():
                try:
                    self._set_skip_version(latest.version)
                except Exception:
                    pass
            return

        if clicked is update_btn:
            if snooze.isChecked():
                try:
                    self._set_skip_version(latest.version)
                except Exception:
                    pass
            self._begin_update(latest)

    def _show_mandatory_dialog(self, latest: UpdateEntry) -> None:
        box = QMessageBox(self._effective_parent())
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Update required")
        box.setText(
            f"This version ({self._app_version}) has been marked as deprecated.\n"
            f"You must update to version {latest.version} to continue using ReNight."
        )

        update_btn = box.addButton("Update now", QMessageBox.AcceptRole)
        releases_btn = box.addButton("Releases", QMessageBox.NoRole)
        quit_btn = box.addButton("Quit", QMessageBox.RejectRole)
        box.setDefaultButton(update_btn)

        box.setWindowModality(Qt.ApplicationModal)
        box.exec()

        clicked = box.clickedButton()
        if clicked is releases_btn:
            open_url_external(DEFAULT_RELEASES_URL)
            self._parent_widget.close()
            return
        if clicked is quit_btn:
            self._parent_widget.close()
            return
        if clicked is update_btn:
            self._begin_update(latest)

    def _begin_update(self, latest: UpdateEntry) -> None:
        if not latest.url:
            open_url_external(DEFAULT_RELEASES_URL)
            return

        if not getattr(sys, "frozen", False):
            open_url_external(latest.url)
            return

        stager = _UpdateStager(
            parent_widget=self._effective_parent(),
            version=latest.version,
            download_url=latest.url,
        )
        stager.start()


class _UpdateStager(QObject):
    """
    Stages a self-update for frozen builds without blocking the UI thread:
      - async download via QNetworkAccessManager
      - extraction in a worker thread (for archives)
      - write update_state to config
      - launch staged binary; quit current app
    """

    def __init__(self, parent_widget: QWidget, version: str, download_url: str) -> None:
        super().__init__(parent_widget)
        self._parent_widget = parent_widget
        self._version = version
        self._download_url = download_url

        self._manager = QNetworkAccessManager(self)
        self._reply: Optional[QNetworkReply] = None
        self._out_f = None

        self._updates_root = _get_updates_dir()
        self._archive_path = ""
        self._stage_dir = ""
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self._on_idle_timeout)

    def start(self) -> None:
        try:
            os.makedirs(self._updates_root, exist_ok=True)
        except OSError as e:
            QMessageBox.warning(
                self._parent_widget,
                "Update failed",
                f"Could not create updates directory:\n{e}",
            )
            open_url_external(self._download_url)
            return

        file_name = self._download_url.rsplit("/", 1)[-1].strip() or f"ReNight-{self._version}"
        self._archive_path = os.path.join(self._updates_root, file_name)

        req = QNetworkRequest(QUrl(self._download_url))
        self._reply = self._manager.get(req)

        try:
            self._out_f = open(self._archive_path, "wb")
        except OSError as e:
            QMessageBox.warning(
                self._parent_widget,
                "Update failed",
                f"Could not open update file for writing:\n{e}",
            )
            open_url_external(self._download_url)
            return

        self._reply.readyRead.connect(self._on_ready_read)
        self._reply.downloadProgress.connect(self._on_progress)
        self._reply.finished.connect(self._on_download_finished)

        self._arm_idle_timeout()

    def _arm_idle_timeout(self) -> None:
        self._idle_timer.start(15000)

    def _on_idle_timeout(self) -> None:
        if self._reply is None:
            return
        try:
            if self._reply.isRunning():
                self._reply.abort()
        except Exception:
            pass

    def _on_ready_read(self) -> None:
        if self._reply is None or self._out_f is None:
            return
        try:
            data = self._reply.readAll()
            b = bytes(data)
            if b:
                self._out_f.write(b)
                self._arm_idle_timeout()
        except Exception:
            pass

    def _on_progress(self, _received: int, _total: int) -> None:
        self._arm_idle_timeout()

    def _on_download_finished(self) -> None:
        self._idle_timer.stop()

        reply = self._reply
        self._reply = None

        try:
            if self._out_f is not None:
                self._out_f.flush()
                self._out_f.close()
        except Exception:
            pass
        self._out_f = None

        if reply is None:
            return

        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                QMessageBox.warning(
                    self._parent_widget,
                    "Update failed",
                    f"Failed to download update:\n{reply.errorString()}",
                )
                return
        finally:
            reply.deleteLater()

        try:
            size = os.path.getsize(self._archive_path)
        except OSError:
            size = 0

        if size <= 0:
            QMessageBox.warning(
                self._parent_widget,
                "Update failed",
                "Downloaded update file is empty; aborting.",
            )
            return

        lower = self._archive_path.lower()

        if lower.endswith(".zip") or lower.endswith(".tar.gz") or lower.endswith(".tgz") or lower.endswith(".tar.bz2") or lower.endswith(".tar"):
            ts = int(time.time())
            safe_ver = self._version.replace("/", "_")
            self._stage_dir = os.path.join(self._updates_root, f"stage-{safe_ver}-{ts}")

            worker = _ExtractorWorker(self._archive_path, self._stage_dir)
            thread = QThread(self)

            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            worker.finished.connect(lambda ok, msg, staged: self._on_extracted(ok, msg, staged, thread, worker))
            worker.finished.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)

            thread.start()
            return

        staged_exe = self._archive_path
        self._finalize_and_launch(staged_exe=staged_exe, stage_dir=self._updates_root)

    def _on_extracted(self, ok: bool, message: str, staged_exe: str, thread: QThread, _worker: QObject) -> None:
        if not ok:
            QMessageBox.warning(self._parent_widget, "Update failed", message)
            return
        self._finalize_and_launch(staged_exe=staged_exe, stage_dir=self._stage_dir)

    def _finalize_and_launch(self, staged_exe: str, stage_dir: str) -> None:
        if sys.platform.startswith("win"):
            old_exe = os.path.abspath(sys.executable)
        else:
            old_exe = os.path.realpath(os.path.abspath(sys.argv[0]))

        cfg = load_config_dict()
        cfg["update_state"] = "staged"
        cfg["update_version"] = self._version
        cfg["update_old_exe"] = old_exe
        cfg["update_staged_exe"] = os.path.abspath(staged_exe)
        cfg["update_stage_dir"] = os.path.abspath(stage_dir) if stage_dir else ""
        cfg["update_archive"] = os.path.abspath(self._archive_path)
        cfg["update_cleanup_exe"] = ""
        save_config_dict(cfg)

        try:
            if sys.platform.startswith("win"):
                os.startfile(staged_exe)  # type: ignore[attr-defined]
            else:
                st = os.stat(staged_exe)
                os.chmod(staged_exe, st.st_mode | 0o111)
                import subprocess

                subprocess.Popen([staged_exe])
        except Exception as e:
            QMessageBox.warning(
                self._parent_widget,
                "Update failed",
                f"Downloaded and staged update, but failed to start the new binary:\n{e}",
            )
            return

        QMessageBox.information(
            self._parent_widget,
            "Update started",
            "The updated ReNight binary has been started.\n"
            "It will copy itself over the original executable and start the updated version.\n"
            "This instance will now exit.",
        )

        app = QApplication.instance()
        if app is not None:
            app.quit()
