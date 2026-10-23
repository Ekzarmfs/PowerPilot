"""
Notification and system service control module for PowerPilot.
High-efficiency implementation using direct Windows Registry (winreg) and PowerPilotNative.
Eliminates heavy PowerShell subprocess overhead.
"""

import subprocess
import winreg
import os
from pathlib import Path

NATIVE_EXE = Path(__file__).parent / "PowerPilotNative.exe"


class NotificationManager:
    """Controls Windows notification and system service settings."""

    REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Notifications\Settings"
    REG_VAL = "NOC_GLOBAL_SETTING_TOASTS_ENABLED"

    def _run_ps(self, command, timeout=10):
        """Run a PowerShell command silently as a fallback.

        Args:
            command: PowerShell command string.
            timeout: Timeout in seconds.

        Returns:
            subprocess.CompletedProcess or None on failure.
        """
        try:
            return subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception:
            return None

    # ── Notifications (Instant winreg, 0 subprocesses) ──────────────

    def disable_notifications(self):
        """Suppress Windows toast notifications via direct Registry API.

        Returns:
            bool: True if the operation succeeded.
        """
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.REG_PATH) as key:
                winreg.SetValueEx(key, self.REG_VAL, 0, winreg.REG_DWORD, 0)
            return True
        except Exception:
            # Fallback to native C# helper
            if NATIVE_EXE.exists():
                try:
                    res = subprocess.run([str(NATIVE_EXE), "notifications", "disable"], capture_output=True, timeout=2)
                    return res.returncode == 0
                except Exception:
                    pass
            return False

    def enable_notifications(self):
        """Restore Windows toast notifications via direct Registry API.

        Returns:
            bool: True if the operation succeeded.
        """
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.REG_PATH) as key:
                winreg.SetValueEx(key, self.REG_VAL, 0, winreg.REG_DWORD, 1)
            return True
        except Exception:
            if NATIVE_EXE.exists():
                try:
                    res = subprocess.run([str(NATIVE_EXE), "notifications", "enable"], capture_output=True, timeout=2)
                    return res.returncode == 0
                except Exception:
                    pass
            return False

    def are_notifications_enabled(self):
        """Check if toast notifications are currently enabled (instant read).

        Returns:
            bool: True if notifications are enabled.
        """
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REG_PATH, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, self.REG_VAL)
                return val != 0
        except FileNotFoundError:
            return True
        except Exception:
            return True

    # ── Bluetooth ──────────────────────────────────────────────────

    def set_bluetooth(self, enabled):
        """Enable or disable Bluetooth adapter.

        Args:
            enabled: True to enable, False to disable.

        Returns:
            bool: True if the operation succeeded.
        """
        action = "Enable" if enabled else "Disable"
        cmd = (
            f'$adapter = Get-PnpDevice -Class Bluetooth '
            f'-ErrorAction SilentlyContinue | '
            f'Where-Object {{ $_.Status -ne "Error" }} | '
            f'Select-Object -First 1; '
            f'if ($adapter) {{ {action}-PnpDevice '
            f'-InstanceId $adapter.InstanceId -Confirm:$false }}'
        )
        result = self._run_ps(cmd)
        return result is not None

    def is_bluetooth_enabled(self):
        """Check if Bluetooth is currently enabled.

        Returns:
            bool: True if Bluetooth is enabled.
        """
        cmd = (
            '$adapter = Get-PnpDevice -Class Bluetooth '
            '-ErrorAction SilentlyContinue | '
            'Where-Object { $_.Status -eq "OK" } | '
            'Select-Object -First 1; '
            'if ($adapter) { "enabled" } else { "disabled" }'
        )
        result = self._run_ps(cmd, timeout=5)
        if result and result.stdout:
            return "enabled" in result.stdout.strip().lower()
        return True

    # ── Windows Update ─────────────────────────────────────────────

    def pause_windows_update(self):
        """Pause Windows Update for 7 days via direct Registry.

        Returns:
            bool: True if the operation succeeded.
        """
        try:
            import datetime
            expiry = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)).isoformat()
            key_path = r"SOFTWARE\Microsoft\WindowsUpdate\UX\Settings"
            with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                winreg.SetValueEx(key, "PauseUpdatesExpiryTime", 0, winreg.REG_SZ, expiry)
            return True
        except Exception:
            cmd = (
                'Set-ItemProperty -Path '
                '"HKLM:\\SOFTWARE\\Microsoft\\WindowsUpdate\\UX\\Settings" '
                '-Name "PauseUpdatesExpiryTime" '
                '-Value (Get-Date).AddDays(7).ToString("o") '
                '-ErrorAction SilentlyContinue'
            )
            result = self._run_ps(cmd)
            return result is not None

    def disable_search_indexing(self):
        """Stop Windows Search Indexing service.

        Returns:
            bool: True if the operation succeeded.
        """
        if NATIVE_EXE.exists():
            try:
                res = subprocess.run([str(NATIVE_EXE), "service", "WSearch", "stop"], capture_output=True, text=True, timeout=3, creationflags=subprocess.CREATE_NO_WINDOW)
                if res and res.stdout and '"success":true' in res.stdout:
                    return True
            except Exception:
                pass

        try:
            res = subprocess.run(["net", "stop", "WSearch", "/y"], capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
            return res.returncode == 0
        except Exception:
            result = self._run_ps("Stop-Service WSearch -Force -ErrorAction SilentlyContinue")
            return result is not None

    def enable_search_indexing(self):
        """Start Windows Search Indexing service.

        Returns:
            bool: True if the operation succeeded.
        """
        if NATIVE_EXE.exists():
            try:
                res = subprocess.run([str(NATIVE_EXE), "service", "WSearch", "start"], capture_output=True, text=True, timeout=3, creationflags=subprocess.CREATE_NO_WINDOW)
                if res and res.stdout and '"success":true' in res.stdout:
                    return True
            except Exception:
                pass

        try:
            res = subprocess.run(["net", "start", "WSearch"], capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
            return res.returncode == 0
        except Exception:
            result = self._run_ps("Start-Service WSearch -ErrorAction SilentlyContinue")
            return result is not None

    def is_search_indexing_running(self):
        """Check if Windows Search Indexing is running.

        Returns:
            bool: True if the service is running.
        """
        if NATIVE_EXE.exists():
            try:
                import json
                res = subprocess.run([str(NATIVE_EXE), "service", "WSearch", "status"], capture_output=True, text=True, timeout=2, creationflags=subprocess.CREATE_NO_WINDOW)
                if res and res.stdout:
                    data = json.loads(res.stdout.strip())
                    return data.get("running", False)
            except Exception:
                pass

        try:
            res = subprocess.run(["sc", "query", "WSearch"], capture_output=True, text=True, timeout=3, creationflags=subprocess.CREATE_NO_WINDOW)
            if res and res.stdout:
                return "RUNNING" in res.stdout.upper()
        except Exception:
            pass
        return False
