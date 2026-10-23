"""
Configuration persistence module for PowerPilot.
Stores user preferences and custom loadouts in JSON under %APPDATA%.
"""

import json
import os


class ConfigManager:
    """Manages app configuration read/write to JSON file."""

    APP_NAME = "PowerPilot"

    def __init__(self):
        self._config_dir = os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")),
            self.APP_NAME,
        )
        self._config_file = os.path.join(self._config_dir, "config.json")
        self._config = self._load()

    def _load(self):
        """Load config from disk, falling back to defaults.

        Returns:
            dict: Configuration dictionary.
        """
        try:
            if os.path.exists(self._config_file):
                with open(self._config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Merge with defaults to ensure all keys exist
                defaults = self._defaults()
                defaults.update(data)
                return defaults
        except Exception:
            pass
        return self._defaults()

    def _defaults(self):
        """Return default configuration values.

        Returns:
            dict: Default config.
        """
        return {
            "autorun": True,
            "theme": "dark",
            "start_minimized": False,
            "excluded_processes": [],
            "custom_loadouts": {},
            "active_loadout": None,
            "first_run": True,
        }

    def save(self):
        """Persist current config to disk.

        Returns:
            bool: True if saved successfully.
        """
        try:
            os.makedirs(self._config_dir, exist_ok=True)
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def get(self, key, default=None):
        """Get a config value by key.

        Args:
            key: Config key name.
            default: Fallback value if key is missing.

        Returns:
            The config value.
        """
        return self._config.get(key, default)

    def set(self, key, value):
        """Set a config value and persist to disk.

        Args:
            key: Config key name.
            value: Value to store.
        """
        self._config[key] = value
        self.save()

    def get_all(self):
        """Get all config as a dict copy."""
        return dict(self._config)

    def reset(self):
        """Reset all config to defaults and save."""
        self._config = self._defaults()
        self.save()
