"""
Autorun management module for PowerPilot.
Manages Windows startup registration via the registry.
"""

import winreg
import sys
import os


class AutoRunManager:
    """Manages app autorun via Windows Registry (HKCU\\Run)."""

    REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    APP_NAME = "PowerPilot"

    def __init__(self):
        self._exe_path = self._get_exe_path()

    def _get_exe_path(self):
        """Get the path to the current executable or script.

        Returns:
            str: Quoted path suitable for registry entry.
        """
        if getattr(sys, "frozen", False):
            # Running as compiled .exe (PyInstaller)
            return f'"{sys.executable}"'
        else:
            # Running as Python script
            main_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "main.py")
            )
            return f'"{sys.executable}" "{main_path}"'

    def is_enabled(self):
        """Check if autorun is currently enabled in the registry.

        Returns:
            bool: True if the autorun entry exists.
        """
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REG_PATH,
                0,
                winreg.KEY_READ,
            )
            try:
                winreg.QueryValueEx(key, self.APP_NAME)
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception:
            return False

    def enable(self):
        """Enable autorun by adding registry entry.

        Returns:
            bool: True if successfully enabled.
        """
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REG_PATH,
                0,
                winreg.KEY_SET_VALUE,
            )
            winreg.SetValueEx(
                key, self.APP_NAME, 0, winreg.REG_SZ, self._exe_path
            )
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    def disable(self):
        """Disable autorun by removing registry entry.

        Returns:
            bool: True if successfully disabled.
        """
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REG_PATH,
                0,
                winreg.KEY_SET_VALUE,
            )
            try:
                winreg.DeleteValue(key, self.APP_NAME)
            except FileNotFoundError:
                pass  # Already removed
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    def set_enabled(self, enabled):
        """Set autorun enabled or disabled.

        Args:
            enabled: True to enable, False to disable.

        Returns:
            bool: True if the operation succeeded.
        """
        return self.enable() if enabled else self.disable()
