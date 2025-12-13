# renight_utils.py
# External URL opener with Linux, so when binaries are compiled
#     they (mostly) avoid LD_LIBRARY_PATH issues with Qt / KDE
#     while opening hyperlinks. tbfh this is the best I can 
#     ship you without going crazy. ¯\_(ツ)_/¯

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Sequence, Union

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

_DEBUG_ENV_VAR = "RENIGHT_URL_DEBUG"


def _debug(msg: str) -> None:
    if os.environ.get(_DEBUG_ENV_VAR):
        try:
            print(f"[renight_utils] {msg}", file=sys.stderr)
        except Exception:
            pass


def _sanitized_env_for_external_open() -> dict[str, str]:
    env = os.environ.copy()
    for key in (
        "LD_LIBRARY_PATH",
        "QT_PLUGIN_PATH",
        "QT_QPA_PLATFORM_PLUGIN_PATH",
    ):
        env.pop(key, None)
    return env


def _spawn_external_opener(argv: Sequence[str], env: dict[str, str], grace_s: float = 0.15) -> bool:
    try:
        proc = subprocess.Popen(
            list(argv),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
        )
    except Exception as e:
        _debug(f"failed to start opener {argv!r}: {e!r}")
        return False

    try:
        rc = proc.wait(timeout=grace_s)
    except subprocess.TimeoutExpired:
        return True

    if rc == 0:
        return True

    _debug(f"opener {argv[0]!r} exited quickly with status {rc}")
    return False


def open_url_external(url: Union[str, QUrl]) -> None:
    if not url:
        return

    if isinstance(url, QUrl):
        qurl = url
    else:
        qurl = QUrl.fromUserInput(str(url))

    if not qurl.isValid():
        _debug(f"invalid URL input: {url!r}")
        return

    url_str = qurl.toString(QUrl.FullyEncoded).strip()
    if not url_str:
        _debug(f"empty URL after normalization: {url!r}")
        return

    if sys.platform.startswith("linux"):
        env = _sanitized_env_for_external_open()

        # Prefer xdg-open, then try gio open (common on GNOME-based systems).
        candidates: list[list[str]] = [
            ["xdg-open", url_str],
            ["gio", "open", url_str],
        ]

        for argv in candidates:
            if shutil.which(argv[0]) is None:
                continue
            if _spawn_external_opener(argv, env=env):
                return

    try:
        ok = QDesktopServices.openUrl(qurl)
        if not ok:
            _debug(f"QDesktopServices.openUrl returned False for: {url_str!r}")
    except Exception as e:
        _debug(f"QDesktopServices.openUrl raised {e!r} for: {url_str!r}")
        return
