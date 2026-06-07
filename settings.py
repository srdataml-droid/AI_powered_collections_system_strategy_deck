"""
settings.py — Geldium AI Collections System: Settings Manager
=============================================================
Handles saving and loading user-configured settings.

Right now it stores:
  - receiver_email  → where alert emails go
  - receiver_name   → personalises the email greeting

Saved to settings.json on disk so settings survive
between sessions (Option B — permanent storage).

During a session, settings live in Streamlit's session_state
so the user doesn't have to re-enter them on every page
(Option A — session use).

Both options working together:
  App starts → load from settings.json into session_state
  User changes email → update session_state immediately (Option A)
  User clicks Save → write to settings.json too (Option B)
  Next session → load from settings.json again → pre-filled
"""

import json
import os
import logging
from dotenv import load_dotenv

load_dotenv()  # load .env variables

logger = logging.getLogger(__name__)

# Path to the JSON file that stores user settings
# Reads from .env if set, otherwise defaults to settings.json
SETTINGS_PATH = os.getenv("SETTINGS_PATH", "settings.json")

# Default settings — used when no settings.json exists yet
DEFAULT_SETTINGS = {
    "receiver_email": "",
    "receiver_name":  "Collections Agent"
}


def load_settings() -> dict:
    """
    Load settings from settings.json.
    If the file doesn't exist yet, return defaults.
    This runs at app startup.
    """
    if not os.path.exists(SETTINGS_PATH):
        logger.info("No settings.json found — using defaults.")
        return DEFAULT_SETTINGS.copy()

    try:
        with open(SETTINGS_PATH, "r") as f:
            saved = json.load(f)

        # Merge with defaults in case new fields were added since last save
        # This prevents KeyErrors if we add new settings in future
        merged = DEFAULT_SETTINGS.copy()
        merged.update(saved)

        logger.info(f"✅ Settings loaded from {SETTINGS_PATH}")
        return merged

    except json.JSONDecodeError:
        # File exists but is corrupted — return defaults
        logger.warning("settings.json is corrupted. Using defaults.")
        return DEFAULT_SETTINGS.copy()

    except Exception as e:
        logger.error(f"Could not load settings: {e}")
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict) -> bool:
    """
    Save settings to settings.json permanently.
    Called when user clicks Save in the dashboard.
    Returns True if saved successfully, False if not.
    """
    try:
        with open(SETTINGS_PATH, "w") as f:
            json.dump(settings, f, indent=2)

        logger.info(f"✅ Settings saved to {SETTINGS_PATH}")
        return True

    except PermissionError:
        logger.error(f"Permission denied writing to {SETTINGS_PATH}")
        return False

    except Exception as e:
        logger.error(f"Could not save settings: {e}")
        return False


def get_sender_info() -> dict:
    """
    Read sender details from environment variables.
    These are set by the business (in .env) — not by users.
    Returns a dict with email, password, and display name.
    """
    return {
        "email":    os.getenv("GELDIUM_SENDER_EMAIL", ""),
        "password": os.getenv("GELDIUM_SENDER_PASSWORD", ""),
        "name":     os.getenv("GELDIUM_SENDER_NAME", "Geldium Collections Team")
    }


def sender_configured() -> bool:
    """
    Check if the business sender credentials are set.
    Used to show a warning in the dashboard if email won't work.
    """
    sender = get_sender_info()
    return bool(sender["email"] and sender["password"])