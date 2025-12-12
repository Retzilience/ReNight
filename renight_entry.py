# renight_entry.py
# Pre-Qt startup handshake: apply staged self-update + cleanup.
# Refactor: use renight_state for config I/O; remove duplicate JSON helpers.

from __future__ import annotations

import os
import shutil
import sys
import tempfile

import resources_rc  # noqa: F401

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from renight_state import load_config_dict, save_config_dict
from renight_ui import ReNightWindow


def _canonical(path: str) -> str:
    return os.path.realpath(os.path.abspath(path))


def _this_exe() -> str:
    """
    Canonical path to the current on-disk launcher.

    On Windows, PyInstaller onefile uses sys.executable.
    On Linux, the thing the user ran is argv[0].
    """
    if sys.platform.startswith("win"):
        return _canonical(sys.executable)
    return _canonical(sys.argv[0])


def _atomic_replace(src: str, dst: str) -> None:
    """
    Safely replace dst with src:
    - copy to a temporary file in the same directory
    - mark as executable
    - os.replace to swap atomically
    """
    parent = os.path.dirname(dst) or "."
    fd, tmp = tempfile.mkstemp(prefix=".rn-upd-", dir=parent)
    os.close(fd)
    try:
        shutil.copy2(src, tmp)
        st = os.stat(tmp)
        os.chmod(tmp, st.st_mode | 0o111)
        os.replace(tmp, dst)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _handle_pending_update_startup() -> None:
    """
    Self-update handshake executed before Qt starts.

    States:
        - 'staged':
            Must be running from the staged binary. Copy staged_exe → old_exe,
            mark state 'copied', then relaunch old_exe and exit.

        - 'copied':
            Must be running from the updated original (old_exe). Clean up the
            staged binary, archive, and staging directory; clear update keys.
    """
    cfg = load_config_dict()
    state = str(cfg.get("update_state", "")).strip()
    if not state:
        return

    staged_exe_cfg = cfg.get("update_staged_exe", "") or ""
    old_exe_cfg = cfg.get("update_old_exe", "") or ""

    staged_exe = _canonical(staged_exe_cfg) if staged_exe_cfg else ""
    old_exe = _canonical(old_exe_cfg) if old_exe_cfg else ""
    this_exe = _this_exe()

    print(f"[ReNight updater] state={state}", flush=True)
    print(f"[ReNight updater] this_exe={this_exe}", flush=True)
    print(f"[ReNight updater] staged_exe={staged_exe}", flush=True)
    print(f"[ReNight updater] old_exe={old_exe}", flush=True)

    if state == "staged":
        if not staged_exe or not old_exe:
            print("[ReNight updater] 'staged' but paths missing; clearing state.", flush=True)
            cfg["update_state"] = ""
            save_config_dict(cfg)
            return

        if this_exe != staged_exe:
            print(
                "[ReNight updater] state='staged' but current process is not "
                "the staged binary; skipping update.",
                flush=True,
            )
            return

        print(f"[ReNight updater] Applying update: {staged_exe} -> {old_exe}", flush=True)
        try:
            os.makedirs(os.path.dirname(old_exe) or ".", exist_ok=True)
            _atomic_replace(staged_exe, old_exe)
        except Exception as e:
            print(f"[ReNight updater] Failed to apply update: {e}", flush=True)
            cfg["update_state"] = ""
            save_config_dict(cfg)
            return

        cfg["update_state"] = "copied"
        cfg["update_cleanup_exe"] = staged_exe
        save_config_dict(cfg)

        try:
            if sys.platform.startswith("win"):
                os.startfile(old_exe)  # type: ignore[attr-defined]
            else:
                st = os.stat(old_exe)
                os.chmod(old_exe, st.st_mode | 0o111)
                import subprocess

                subprocess.Popen([old_exe])
        except Exception as e:
            print(f"[ReNight updater] Failed to launch updated binary: {e}", flush=True)
            return

        sys.exit(0)

    if state == "copied":
        if not old_exe:
            print(
                "[ReNight updater] state='copied' but update_old_exe is empty; clearing state.",
                flush=True,
            )
            for key in (
                "update_state",
                "update_version",
                "update_old_exe",
                "update_staged_exe",
                "update_stage_dir",
                "update_archive",
                "update_cleanup_exe",
            ):
                cfg.pop(key, None)
            save_config_dict(cfg)
            return

        if this_exe != old_exe:
            print(
                "[ReNight updater] state='copied' but current process is not "
                "the updated launcher; skipping cleanup.",
                flush=True,
            )
            return

        cleanup_exe = cfg.get("update_cleanup_exe", "") or ""
        stage_dir = cfg.get("update_stage_dir", "") or ""
        archive = cfg.get("update_archive", "") or ""

        if cleanup_exe and os.path.isfile(cleanup_exe):
            try:
                print(f"[ReNight updater] Cleaning up staged exe: {cleanup_exe}", flush=True)
                os.remove(cleanup_exe)
            except OSError as e:
                print(f"[ReNight updater] Failed to remove staged exe {cleanup_exe}: {e}", flush=True)

        if archive and os.path.isfile(archive):
            try:
                print(f"[ReNight updater] Cleaning up update archive: {archive}", flush=True)
                os.remove(archive)
            except OSError as e:
                print(f"[ReNight updater] Failed to remove update archive {archive}: {e}", flush=True)

        if stage_dir and os.path.isdir(stage_dir):
            try:
                print(f"[ReNight updater] Cleaning up stage dir: {stage_dir}", flush=True)
                shutil.rmtree(stage_dir)
            except OSError as e:
                print(f"[ReNight updater] Failed to remove stage dir {stage_dir}: {e}", flush=True)

        for key in (
            "update_state",
            "update_version",
            "update_old_exe",
            "update_staged_exe",
            "update_stage_dir",
            "update_archive",
            "update_cleanup_exe",
        ):
            cfg.pop(key, None)

        save_config_dict(cfg)


def main() -> None:
    _handle_pending_update_startup()

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(":/icons/ReNight.ico"))

    window = ReNightWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
