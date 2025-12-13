# renight_utils.py
# External URL opener with Linux, so when binaries are compiled they don't bug out with KDE opening Qt links. ¯\_(ツ)_/¯ 

from __future__ import annotations

import os
import subprocess
import sys
from typing import Union

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


def open_url_external(url: Union[str, QUrl]) -> None:
    if not url:
        return

    if isinstance(url, QUrl):
        qurl = url
        url_str = qurl.toString()
    else:
        url_str = str(url)
        qurl = QUrl(url_str)

    if sys.platform.startswith("linux"):
        try:
            env = os.environ.copy()
            for key in (
                "LD_LIBRARY_PATH",
                "QT_PLUGIN_PATH",
                "QT_QPA_PLATFORM_PLUGIN_PATH",
            ):
                env.pop(key, None)
            subprocess.Popen(["xdg-open", url_str], env=env)
            return
        except Exception:
            pass

    try:
        QDesktopServices.openUrl(qurl)
    except Exception:
        return
