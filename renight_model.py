import os
import json
import shutil
from typing import List, Tuple

from renight_core import (
    CONFIG_FILE,
    MOD_DB_FILE,
    get_default_nightdive_folder,
    compute_md5,
    generate_unique_dest_name,
    get_config_path,
    get_mod_db_path,
)


class ReNightModel:
    """
    Logic: config, metadata, import, scan, delete. No Qt dependencies.

    UI code should call:
        - set_nightdive_folder / set_pwad_folder / set_symlink_option
        - import_mods(selected_files)
        - scan_mods()
        - delete_mods(mod_names)

    It also owns update-related state that is persisted in the config file.
    """

    def __init__(self) -> None:
        self.nightdive_folder: str = os.path.normpath(
            get_default_nightdive_folder()
        )
        self.pwad_folder: str = ""
        self.symlink_option: bool = True

        self.mod_metadata: dict[str, dict[str, str]] = {}

        # Update-related state persisted in the config file.
        self.last_update_check: float = 0.0
        self.snoozed_version: str = ""

        # Self-updater staging state.
        self.update_state: str = ""
        self.update_version: str = ""
        self.update_old_exe: str = ""
        self.update_staged_exe: str = ""
        self.update_stage_dir: str = ""
        self.update_archive: str = ""
        self.update_cleanup_exe: str = ""

        self._load_config()
        self._load_mod_metadata()

    # ----- config -----

    def _get_config_path(self) -> str:
        return get_config_path()

    def _load_config(self) -> None:
        config_path = self._get_config_path()
        print(f"Config path: {config_path}")

        if os.path.isfile(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                self.nightdive_folder = os.path.normpath(
                    config.get("nightdive_folder", self.nightdive_folder)
                )
                self.pwad_folder = os.path.normpath(
                    config.get("pwad_folder", self.pwad_folder)
                )
                self.symlink_option = config.get(
                    "symlink_option", self.symlink_option
                )
                self.last_update_check = float(
                    config.get("last_update_check", self.last_update_check)
                )
                self.snoozed_version = str(
                    config.get("snoozed_version", self.snoozed_version)
                )

                self.update_state = str(
                    config.get("update_state", self.update_state)
                )
                self.update_version = str(
                    config.get("update_version", self.update_version)
                )
                self.update_old_exe = os.path.normpath(
                    config.get("update_old_exe", self.update_old_exe)
                )
                self.update_staged_exe = os.path.normpath(
                    config.get("update_staged_exe", self.update_staged_exe)
                )
                self.update_stage_dir = os.path.normpath(
                    config.get("update_stage_dir", self.update_stage_dir)
                )
                self.update_archive = os.path.normpath(
                    config.get("update_archive", self.update_archive)
                )
                self.update_cleanup_exe = os.path.normpath(
                    config.get("update_cleanup_exe", self.update_cleanup_exe)
                )
            except Exception as e:
                print(f"Error loading config: {e}")

    def _save_config(self) -> None:
        config = {
            "nightdive_folder": os.path.normpath(self.nightdive_folder),
            "pwad_folder": os.path.normpath(self.pwad_folder),
            "symlink_option": bool(self.symlink_option),
            "last_update_check": float(self.last_update_check),
            "snoozed_version": self.snoozed_version,
            "update_state": self.update_state,
            "update_version": self.update_version,
            "update_old_exe": os.path.normpath(self.update_old_exe),
            "update_staged_exe": os.path.normpath(self.update_staged_exe),
            "update_stage_dir": os.path.normpath(self.update_stage_dir),
            "update_archive": os.path.normpath(self.update_archive),
            "update_cleanup_exe": os.path.normpath(self.update_cleanup_exe),
        }

        config_path = self._get_config_path()
        print(f"Saving config to: {config_path}")
        try:
            with open(config_path, "w") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def set_nightdive_folder(self, path: str) -> None:
        self.nightdive_folder = os.path.normpath(path)
        self._save_config()

    def set_pwad_folder(self, path: str) -> None:
        self.pwad_folder = os.path.normpath(path)
        self._save_config()

    def set_symlink_option(self, value: bool) -> None:
        self.symlink_option = bool(value)
        self._save_config()

    # ----- metadata -----

    def _get_mod_db_path(self) -> str:
        return get_mod_db_path()

    def _load_mod_metadata(self) -> None:
        db_path = self._get_mod_db_path()
        self.mod_metadata = {}

        if os.path.isfile(db_path):
            try:
                with open(db_path, "r") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.mod_metadata = data
            except Exception as e:
                print(f"Error loading mod metadata: {e}")

    def _save_mod_metadata(self) -> None:
        db_path = self._get_mod_db_path()
        print(f"Saving mod metadata to: {db_path}")
        try:
            with open(db_path, "w") as f:
                json.dump(self.mod_metadata, f, indent=4)
        except Exception as e:
            print(f"Error saving mod metadata: {e}")

    # ----- import -----

    def import_mods(self, selected_files: List[str]) -> Tuple[bool, bool, List[str]]:
        """
        Import the given WADs. Returns (any_success, any_failure, messages).
        """
        messages: List[str] = []

        if not selected_files:
            messages.append("No files selected for import.")
            return False, True, messages

        target_folder = self.nightdive_folder
        if not os.path.isdir(target_folder):
            messages.append(f"Nightdive folder does not exist: {target_folder}")
            return False, True, messages

        use_symlink = self.symlink_option

        any_success = False
        any_failure = False

        for wad_path in selected_files:
            if not os.path.isfile(wad_path):
                messages.append(f"Source file not found: {wad_path}")
                any_failure = True
                continue

            dest_name = os.path.basename(wad_path)
            dest_path = os.path.join(target_folder, dest_name)

            if use_symlink:
                try:
                    if os.path.exists(dest_path) or os.path.islink(dest_path):
                        os.unlink(dest_path)
                    os.symlink(wad_path, dest_path)
                    messages.append(f"Created symlink for: {dest_path}")
                    self.mod_metadata[dest_name] = {
                        "source": os.path.normpath(wad_path),
                        "mode": "symlink",
                    }
                    any_success = True
                except OSError as e:
                    messages.append(f"Error processing {wad_path}: {e}")
                    any_failure = True
                continue

            # Copy mode: handle collisions.
            try:
                src_md5 = compute_md5(wad_path)
            except OSError as e:
                messages.append(f"Error reading {wad_path}: {e}")
                any_failure = True
                continue

            if os.path.exists(dest_path):
                existing_md5 = None
                try:
                    existing_md5 = compute_md5(dest_path)
                except OSError:
                    existing_md5 = None

                if existing_md5 is not None and existing_md5 != src_md5:
                    new_name = generate_unique_dest_name(dest_name, target_folder)
                    dest_name = new_name
                    dest_path = os.path.join(target_folder, dest_name)

            try:
                if os.path.exists(dest_path):
                    os.unlink(dest_path)
                shutil.copyfile(wad_path, dest_path)
                messages.append(f"Copied file to: {dest_path}")
                self.mod_metadata[dest_name] = {
                    "source": os.path.normpath(wad_path),
                    "mode": "copy",
                    "md5": src_md5,
                }
                any_success = True
            except OSError as e:
                messages.append(f"Error processing {wad_path}: {e}")
                any_failure = True

        self._save_mod_metadata()
        return any_success, any_failure, messages

    # ----- scan / classification -----

    def scan_mods(self) -> List[Tuple[str, str]]:
        """
        Return list of (prefix, filename) for the Nightdive folder.

        CPY vs ONL is recomputed every time:
        - Metadata is only trusted if the recorded source file still exists.
        - Otherwise, MD5 is compared against all WADs in the PWAD tree.
        - If no current match exists, the entry is downgraded to ONL and its metadata is removed.
        """
        entries: List[Tuple[str, str]] = []
        target_folder = self.nightdive_folder
        pwad_folder = self.pwad_folder.strip()

        if not os.path.isdir(target_folder):
            return entries

        pwad_index: dict[str, list[str]] = {}
        if pwad_folder and os.path.isdir(pwad_folder):
            for root, _, files in os.walk(pwad_folder):
                for filename in files:
                    if filename.lower().endswith(".wad"):
                        pwad_index.setdefault(filename.lower(), []).append(
                            os.path.join(root, filename)
                        )

        md5_cache: dict[str, str] = {}
        metadata_changed = False
        seen_names: set[str] = set()

        for item in os.listdir(target_folder):
            full_path = os.path.join(target_folder, item)

            if not (item.lower().endswith(".wad") or os.path.islink(full_path)):
                continue

            seen_names.add(item)

            if os.path.islink(full_path):
                entries.append(("(SL)", item))
                continue

            prefix = "(ONL)"

            # Compute dest MD5 once, used for both metadata verification and PWAD scan.
            dest_md5 = None
            try:
                dest_md5 = compute_md5(full_path, md5_cache)
            except OSError:
                dest_md5 = None

            meta = self.mod_metadata.get(item)
            meta_mode = meta.get("mode") if isinstance(meta, dict) else None
            meta_source = meta.get("source") if isinstance(meta, dict) else None
            meta_md5 = meta.get("md5") if isinstance(meta, dict) else None
            used_metadata = False

            # 1) Try to validate existing metadata if it still points to a real file.
            if (
                dest_md5
                and meta_mode == "copy"
                and meta_source
                and os.path.isfile(meta_source)
            ):
                if meta_md5 and meta_md5 != dest_md5:
                    self.mod_metadata[item]["md5"] = dest_md5
                    metadata_changed = True
                prefix = "(CPY)"
                used_metadata = True
            else:
                if meta is not None:
                    self.mod_metadata.pop(item, None)
                    metadata_changed = True

            # 2) If metadata did not validate, attempt auto-detection against PWAD tree.
            if not used_metadata and dest_md5:
                candidates = pwad_index.get(item.lower(), [])
                for src_path in candidates:
                    if not os.path.isfile(src_path):
                        continue
                    try:
                        src_md5 = compute_md5(src_path, md5_cache)
                    except OSError:
                        continue
                    if src_md5 == dest_md5:
                        prefix = "(CPY)"
                        self.mod_metadata[item] = {
                            "source": os.path.normpath(src_path),
                            "mode": "copy",
                            "md5": dest_md5,
                        }
                        metadata_changed = True
                        break

            entries.append((prefix, item))

        # Clean up metadata for files that no longer exist in Nightdive folder.
        removed = [
            name for name in list(self.mod_metadata.keys()) if name not in seen_names
        ]
        if removed:
            for name in removed:
                self.mod_metadata.pop(name, None)
            metadata_changed = True

        if metadata_changed:
            self._save_mod_metadata()

        return entries

    # ----- delete -----

    def delete_mods(self, mod_names: List[str]) -> List[str]:
        """
        Delete the given mods from the Nightdive folder.
        Returns console messages.
        """
        messages: List[str] = []
        target_folder = self.nightdive_folder
        changed = False

        for mod_name in mod_names:
            full_path = os.path.join(target_folder, mod_name)
            print(f"Attempting to delete: {full_path}")
            try:
                if os.path.exists(full_path) or os.path.islink(full_path):
                    os.unlink(full_path)
                    changed = True
                    self.mod_metadata.pop(mod_name, None)
                    messages.append(f"Deleted mod: {full_path}")
                else:
                    messages.append(f"Mod not found: {full_path}")
            except OSError as e:
                messages.append(f"Error deleting {full_path}: {e}")

        if changed:
            self._save_mod_metadata()

        return messages
