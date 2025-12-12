# renight_updater.py
# Update checker only: fetch descriptor, compare versions, and open download/release URLs.
# No staging, no self-replacement, no update_state persistence.

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from PySide6.QtCore import QObject, QTimer, QUrl, Qt
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QApplication, QCheckBox, QMessageBox, QWidget

from renight_core import UPDATE_INFO_URL, compare_versions
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

    Preferred format:
        version | os | flags,flags,... | download_url

    Compatibility:
        - If a line has >4 parts, extra parts are ignored.
        - If a line has exactly 3 parts, it is treated as: version|os|url with empty flags.
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


class UpdateClient(QObject):
    """
    Update checker only:
      - descriptor fetch via QNetworkAccessManager
      - in-flight guard
      - explicit timeout
      - skip/snooze handling via callbacks
      - optional/mandatory dialogs that open a URL
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
        _raw_text: str,
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

    def _best_update_url(self, latest: UpdateEntry) -> str:
        url = (latest.url or "").strip()
        return url if url else DEFAULT_RELEASES_URL

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

        download_btn = box.addButton("Download", QMessageBox.AcceptRole)
        releases_btn = box.addButton("Releases", QMessageBox.NoRole)
        later_btn = box.addButton("Later", QMessageBox.RejectRole)
        box.setDefaultButton(download_btn)

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

        if snooze.isChecked():
            try:
                self._set_skip_version(latest.version)
            except Exception:
                pass

        if clicked is releases_btn:
            open_url_external(DEFAULT_RELEASES_URL)
            return

        if clicked is download_btn:
            open_url_external(self._best_update_url(latest))
            return

    def _show_mandatory_dialog(self, latest: UpdateEntry) -> None:
        box = QMessageBox(self._effective_parent())
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Update required")
        box.setText(
            f"This version ({self._app_version}) has been marked as deprecated.\n"
            f"You must update to version {latest.version} to continue using ReNight."
        )

        download_btn = box.addButton("Download", QMessageBox.AcceptRole)
        releases_btn = box.addButton("Releases", QMessageBox.NoRole)
        quit_btn = box.addButton("Quit", QMessageBox.RejectRole)
        box.setDefaultButton(download_btn)

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
        if clicked is download_btn:
            open_url_external(self._best_update_url(latest))
            self._parent_widget.close()
            return
