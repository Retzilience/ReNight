# renight_state.py
# not really being used, part of a update staging experiment
# Non-Qt helpers for reading/writing config state, shared by entry + updater.

from __future__ import annotations

import json
import os
from typing import Any, Dict

from renight_core import get_config_path


def load_config_dict() -> Dict[str, Any]:
    """
    Load the raw JSON config as a dict. Returns {} on any error.
    """
    path = get_config_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_config_dict(cfg: Dict[str, Any]) -> None:
    """
    Write the raw JSON config dict. Fail-soft.
    """
    path = get_config_path()
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    except OSError:
        pass
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
    except Exception:
        return
