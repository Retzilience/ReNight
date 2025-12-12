import os
import sys
import hashlib
import shutil

VERSION = "0.1a"

CONFIG_FILE = "ReNight_config.json"
MOD_DB_FILE = "ReNight_mods.json"

# URL of the update descriptor file hosted in the repository.
UPDATE_INFO_URL = "https://raw.githubusercontent.com/Retzilience/ReNight/main/version.upd"


def resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    """
    try:
        # noinspection PyUnresolvedReferences,PyProtectedMember
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_app_directory() -> str:
    """
    Get the directory where the executable or script is located.
    This is primarily used for locating bundled resources, not for config.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def get_config_directory() -> str:
    """
    Return an OS-appropriate per-user directory for configuration/state.
    - Windows: %APPDATA%\\ReNight
    - Linux:   ~/.config/ReNight
    """
    home = os.path.expanduser("~")
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA", home)
        return os.path.join(base, "ReNight")
    else:
        return os.path.join(home, ".config", "ReNight")


def get_data_directory() -> str:
    """
    Return an OS-appropriate per-user directory for data (updates, caches, etc.).
    - Windows: %LOCALAPPDATA%\\ReNight
    - Linux:   ~/.local/share/ReNight
    """
    home = os.path.expanduser("~")
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA", home)
        return os.path.join(base, "ReNight")
    else:
        return os.path.join(home, ".local", "share", "ReNight")


def get_config_path() -> str:
    """
    Return the full path to the JSON config file, migrating from legacy
    side-by-side config in the app directory if needed.
    """
    cfg_dir = get_config_directory()
    os.makedirs(cfg_dir, exist_ok=True)
    new_path = os.path.join(cfg_dir, CONFIG_FILE)

    # Legacy location: next to the executable / script.
    legacy_path = os.path.join(get_app_directory(), CONFIG_FILE)
    if not os.path.isfile(new_path) and os.path.isfile(legacy_path):
        try:
            shutil.copy2(legacy_path, new_path)
        except OSError:
            # If migration fails, we still just fall back to the new path.
            pass

    return new_path


def get_mod_db_path() -> str:
    """
    Return the full path to the mod metadata DB, migrating from legacy
    side-by-side DB in the app directory if needed.
    """
    cfg_dir = get_config_directory()
    os.makedirs(cfg_dir, exist_ok=True)
    new_path = os.path.join(cfg_dir, MOD_DB_FILE)

    legacy_path = os.path.join(get_app_directory(), MOD_DB_FILE)
    if not os.path.isfile(new_path) and os.path.isfile(legacy_path):
        try:
            shutil.copy2(legacy_path, new_path)
        except OSError:
            pass

    return new_path


def get_default_nightdive_folder() -> str:
    """
    Heuristic default for Nightdive DOOM folder.

    - Windows: ~/Saved Games/Nightdive Studios/DOOM
    - Linux: try Proton compatdata for appid 2280 (with kexengine.cfg),
      then scan compatdata for any matching DOOM folder with kexengine.cfg,
      otherwise fall back to the Windows-style path in $HOME.
    """
    user_home = os.path.expanduser("~")

    # Windows / WSL case
    if os.name == "nt":
        return os.path.join(
            user_home,
            "Saved Games",
            "Nightdive Studios",
            "DOOM",
        )

    # Linux Proton heuristic
    if sys.platform.startswith("linux"):
        compat_root = os.path.join(
            user_home,
            ".local",
            "share",
            "Steam",
            "steamapps",
            "compatdata",
        )

        # First try the canonical appid path
        appid_path = os.path.join(
            compat_root,
            "2280",
            "pfx",
            "drive_c",
            "users",
            "steamuser",
            "Saved Games",
            "Nightdive Studios",
            "DOOM",
        )
        cfg_path = os.path.join(appid_path, "kexengine.cfg")
        if os.path.isdir(appid_path) and os.path.isfile(cfg_path):
            return appid_path

        # Generic scan over compatdata/*, but only at the expected subpath.
        if os.path.isdir(compat_root):
            for entry in os.listdir(compat_root):
                base = os.path.join(
                    compat_root,
                    entry,
                    "pfx",
                    "drive_c",
                    "users",
                    "steamuser",
                    "Saved Games",
                    "Nightdive Studios",
                    "DOOM",
                )
                cfg = os.path.join(base, "kexengine.cfg")
                if os.path.isdir(base) and os.path.isfile(cfg):
                    return base

    # Fallback (non-Steam Wine, etc.)
    return os.path.join(user_home, "Saved Games", "Nightdive Studios", "DOOM")


def compute_md5(path: str, cache: dict | None = None) -> str:
    """
    Compute MD5 for a file, optionally using a shared cache.
    """
    if cache is not None and path in cache:
        return cache[path]

    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    digest = h.hexdigest()

    if cache is not None:
        cache[path] = digest
    return digest


def generate_unique_dest_name(base_name: str, target_folder: str) -> str:
    """
    Generate 'name-2.wad', 'name-3.wad', ... until a free name is found.
    """
    name, ext = os.path.splitext(base_name)
    candidate = base_name
    counter = 2
    while os.path.exists(os.path.join(target_folder, candidate)):
        candidate = f"{name}-{counter}{ext}"
        counter += 1
    return candidate


def _version_to_tuple(version: str) -> tuple[int, ...]:
    """
    Convert a version string like '0.02', '0.3.1', '0.3-beta' into a numeric tuple.
    Non-numeric suffixes (e.g. '-beta') are ignored for the numeric comparison.
    """
    s = version.strip()

    # Strip any suffix starting at first non-digit/non-dot character.
    end = 0
    while end < len(s) and (s[end].isdigit() or s[end] == "."):
        end += 1
    s = s[:end]

    if not s:
        return (0,)

    parts = s.split(".")
    out: list[int] = []
    for p in parts:
        if not p:
            out.append(0)
        else:
            try:
                out.append(int(p))
            except ValueError:
                out.append(0)
    return tuple(out)


def _is_beta_version(version: str) -> bool:
    """
    Return True if the version string looks like a beta build.
    """
    s = version.strip().lower()
    if "beta" in s:
        return True
    if s.endswith("b"):
        return True
    return False


def compare_versions(a: str, b: str) -> int:
    """
    Compare two version strings.

    Returns:
        -1 if a < b
         0 if a == b
         1 if a > b

    Beta builds are considered lower than a stable of the same numeric version:
    '0.03-beta' < '0.03'.
    """
    ta = _version_to_tuple(a)
    tb = _version_to_tuple(b)

    max_len = max(len(ta), len(tb))
    ta = ta + (0,) * (max_len - len(ta))
    tb = tb + (0,) * (max_len - len(tb))

    if ta < tb:
        return -1
    if ta > tb:
        return 1

    # Numeric parts are equal; apply beta vs stable rule.
    a_beta = _is_beta_version(a)
    b_beta = _is_beta_version(b)
    if a_beta and not b_beta:
        return -1
    if b_beta and not a_beta:
        return 1
    return 0
