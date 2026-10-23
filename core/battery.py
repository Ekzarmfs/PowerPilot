"""
Battery monitoring module for PowerPilot.
Uses psutil for real-time battery status and WMI for health diagnostics.
"""

import psutil
import subprocess
import re
import threading
import time
import ctypes
from ctypes import wintypes

class _SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ('ACLineStatus', wintypes.BYTE),
        ('BatteryFlag', wintypes.BYTE),
        ('BatteryLifePercent', wintypes.BYTE),
        ('SystemStatusFlag', wintypes.BYTE),
        ('BatteryLifeTime', wintypes.DWORD),
        ('BatteryFullLifeTime', wintypes.DWORD),
    ]


class BatteryMonitor:
    """Monitors battery status and health on Windows."""

    def __init__(self):
        self._callbacks = []
        self._running = False
        self._thread = None
        self._health_info = None

    def get_status(self):
        """Get current battery status.

        Returns:
            dict: Battery status including percent, plugged state, time remaining.
        """
        # Fast path: In-process Win32 GetSystemPowerStatus (0.01ms)
        try:
            status = _SYSTEM_POWER_STATUS()
            if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
                plugged = (status.ACLineStatus == 1)
                percent = int(status.BatteryLifePercent)
                if percent <= 100:
                    time_secs = status.BatteryLifeTime
                    if plugged:
                        time_str = "Plugged In"
                        st = "Fully Charged" if percent >= 100 else "Charging"
                    elif time_secs == 4294967295 or time_secs < 0 or time_secs > 86400:
                        time_str = "Calculating..."
                        st = "On Battery"
                    else:
                        h = time_secs // 3600
                        m = (time_secs % 3600) // 60
                        time_str = f"{h}h {m}m"
                        st = "On Battery"
                    return {
                        "available": True,
                        "percent": percent,
                        "plugged": plugged,
                        "time_left": time_str,
                        "time_left_seconds": time_secs,
                        "status": st,
                    }
        except Exception:
            pass

        battery = psutil.sensors_battery()
        if battery is None:
            return {
                "available": False,
                "percent": 0,
                "plugged": False,
                "time_left": "N/A",
                "time_left_seconds": 0,
                "status": "No Battery Detected",
            }

        time_left = battery.secsleft
        if time_left == psutil.POWER_TIME_UNLIMITED:
            time_str = "Plugged In"
            time_secs = -1
        elif time_left == psutil.POWER_TIME_UNKNOWN:
            time_str = "Calculating..."
            time_secs = -1
        else:
            hours = time_left // 3600
            minutes = (time_left % 3600) // 60
            time_str = f"{hours}h {minutes}m"
            time_secs = time_left

        if battery.power_plugged:
            if battery.percent >= 100:
                status = "Fully Charged"
            else:
                status = "Charging"
        else:
            status = "On Battery"

        return {
            "available": True,
            "percent": battery.percent,
            "plugged": battery.power_plugged,
            "time_left": time_str,
            "time_left_seconds": time_secs,
            "status": status,
        }

    def get_health(self):
        """Get battery health information via WMI (non-blocking).

        Returns:
            dict: Battery health data including design/full capacity and health %.
        """
        if self._health_info is not None:
            return self._health_info

        if not getattr(self, "_health_fetching", False):
            self._health_fetching = True
            threading.Thread(target=self._fetch_health_background, daemon=True).start()

        return self._default_health()

    def _fetch_health_background(self):
        """Worker thread to query WMI battery health without blocking GUI."""
        from pathlib import Path
        import json
        native_exe = Path(__file__).parent / "PowerPilotNative.exe"
        if native_exe.exists():
            try:
                res = subprocess.run([str(native_exe), "battery"], capture_output=True, text=True, timeout=3, creationflags=subprocess.CREATE_NO_WINDOW)
                if res and res.stdout:
                    data = json.loads(res.stdout.strip())
                    health = data.get("health", {})
                    if health.get("available") and health.get("designed_capacity_mwh", 0) > 0:
                        self._health_info = {
                            "designed_capacity_mwh": health["designed_capacity_mwh"],
                            "full_charge_capacity_mwh": health["full_charge_capacity_mwh"],
                            "health_percent": health["health_percent"],
                            "available": True,
                        }
                        self._health_fetching = False
                        return
            except Exception:
                pass

        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-Command",
                    (
                        "Get-WmiObject -Class BatteryStaticData -Namespace ROOT/WMI "
                        "| Select-Object -Property DesignedCapacity; "
                        "Get-WmiObject -Class BatteryFullChargedCapacity -Namespace ROOT/WMI "
                        "| Select-Object -Property FullChargedCapacity"
                    ),
                ],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            output = result.stdout
            designed = re.search(r"DesignedCapacity\s*:\s*(\d+)", output)
            full = re.search(r"FullChargedCapacity\s*:\s*(\d+)", output)

            if designed and full:
                designed_cap = int(designed.group(1))
                full_cap = int(full.group(1))
                health_pct = (
                    round((full_cap / designed_cap) * 100, 1)
                    if designed_cap > 0
                    else 100
                )
                self._health_info = {
                    "designed_capacity_mwh": designed_cap,
                    "full_charge_capacity_mwh": full_cap,
                    "health_percent": min(health_pct, 100),
                    "available": True,
                }
            else:
                self._health_info = self._default_health()
        except Exception:
            self._health_info = self._default_health()
        finally:
            self._health_fetching = False

    def _default_health(self):
        """Return default health info when data is unavailable."""
        return {
            "designed_capacity_mwh": 0,
            "full_charge_capacity_mwh": 0,
            "health_percent": 100,
            "available": False,
        }

    def register_callback(self, callback):
        """Register a callback for battery status updates.

        Args:
            callback: Function accepting a battery status dict.
        """
        self._callbacks.append(callback)

    def unregister_callback(self, callback):
        """Unregister a previously registered callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def start_monitoring(self, interval=5):
        """Start periodic battery monitoring in a background thread.

        Args:
            interval: Seconds between updates (default 5).
        """
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop, args=(interval,), daemon=True
        )
        self._thread.start()

    def stop_monitoring(self):
        """Stop the battery monitoring thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _monitor_loop(self, interval):
        """Internal monitoring loop running in background thread."""
        while self._running:
            status = self.get_status()
            for cb in self._callbacks:
                try:
                    cb(status)
                except Exception:
                    pass
            time.sleep(interval)
