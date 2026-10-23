"""
Background process optimizer for PowerPilot.
Scans all running processes (background and active), categorizes them,
and allows the user to disable non-essential ones for battery savings.
"""

import psutil
import os
import threading
import time
import subprocess
import json
from pathlib import Path

NATIVE_EXE = Path(__file__).parent / "PowerPilotNative.exe"


class ProcessInfo:
    """Holds metadata about a single process for the optimizer."""

    def __init__(self, pid, name, cpu_percent, memory_mb, status,
                 category, is_mandatory, description=""):
        self.pid = pid
        self.name = name
        self.cpu_percent = cpu_percent
        self.memory_mb = memory_mb
        self.status = status
        self.category = category          # "windows", "microsoft", "third_party", "user"
        self.is_mandatory = is_mandatory   # True = must not be killed
        self.description = description
        self.is_enabled = True             # User toggle state

    def to_dict(self):
        return {
            "pid": self.pid,
            "name": self.name,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "status": self.status,
            "category": self.category,
            "is_mandatory": self.is_mandatory,
            "description": self.description,
            "is_enabled": self.is_enabled,
        }


class BackgroundProcessManager:
    """Scans and manages all background processes for battery optimization."""

    # ── Mandatory system processes (NEVER kill) ────────────────────
    MANDATORY_PROCESSES = {
        "system", "system idle process", "registry", "smss.exe",
        "csrss.exe", "wininit.exe", "services.exe", "lsass.exe",
        "winlogon.exe", "logonui.exe", "dwm.exe", "explorer.exe",
        "ntoskrnl.exe", "fontdrvhost.exe", "memory compression",
        "secure system", "idle", "csrss", "svchost.exe",
        "lsaiso.exe", "wudfhost.exe", "msdtc.exe",
    }

    # ── Windows/Microsoft background processes ─────────────────────
    WINDOWS_BG_PROCESSES = {
        # Cortana / Search
        "searchhost.exe": "Windows Search Host",
        "searchindexer.exe": "Windows Search Indexer",
        "searchprotocolhost.exe": "Search Protocol Host",
        "searchfilterhost.exe": "Search Filter Host",
        "searchapp.exe": "Windows Search App",
        # Shell / UX
        "shellexperiencehost.exe": "Shell Experience Host",
        "startmenuexperiencehost.exe": "Start Menu Experience",
        "runtimebroker.exe": "Runtime Broker (UWP)",
        "applicationframehost.exe": "Application Frame Host",
        "textinputhost.exe": "Text Input Service",
        "widgetservice.exe": "Windows Widgets Service",
        "widgets.exe": "Windows Widgets",
        "lockapp.exe": "Lock Screen App",
        "systemsettings.exe": "Windows Settings App",
        "ctfmon.exe": "CTF Loader (Input)",
        "sihost.exe": "Shell Infrastructure Host",
        "taskhostw.exe": "Task Host Window",
        # Security (non-mandatory background)
        "securityhealthservice.exe": "Windows Security Service",
        "securityhealthsystray.exe": "Windows Security Systray",
        "smartscreen.exe": "SmartScreen Filter",
        "sgrmbroker.exe": "System Guard Runtime",
        # Windows Update
        "usoclient.exe": "Windows Update Client",
        "musnotification.exe": "Update Notification",
        # Telemetry & Diagnostics
        "compattelrunner.exe": "Compatibility Telemetry",
        "devicecensus.exe": "Device Census",
        "diagtrack.exe": "Diagnostics Tracking",
        "wermgr.exe": "Windows Error Reporting",
        "wermsgsv.exe": "WER Message Service",
        # Background tasks
        "backgroundtaskhost.exe": "Background Task Host",
        "backgroundtransferhost.exe": "Background Transfer Host",
        "dllhost.exe": "COM Surrogate",
        "conhost.exe": "Console Window Host",
        "dashost.exe": "Device Association Host",
        "wmiprvse.exe": "WMI Provider Host",
        "unsecapp.exe": "WMI Unsecapp",
        # Miscellaneous
        "gamebarpresencewriter.exe": "Game Bar Presence Writer",
        "gamebarftserver.exe": "Game Bar Full Trust Server",
        "gamelaunchhelper.exe": "Game Launch Helper",
        "yourphone.exe": "Phone Link App",
        "phoneexperiencehost.exe": "Phone Link Experience",
        "msedgewebview2.exe": "Edge WebView2 Runtime",
        "msteams.exe": "Microsoft Teams",
        "onedrive.exe": "OneDrive Sync",
        "skypeapp.exe": "Skype",
        "outlook.exe": "Microsoft Outlook",
        "teams.exe": "Microsoft Teams (New)",
        # Spooler / Print
        "spoolsv.exe": "Print Spooler Service",
        # Audio (usually OK to keep)
        "audiodg.exe": "Windows Audio Device Graph",
        # Networking
        "wlanext.exe": "WLAN Extensibility",
        "openssh-agent.exe": "OpenSSH Agent",
    }

    # ── Known Microsoft processes ──────────────────────────────────
    MICROSOFT_IDENTIFIERS = {
        "microsoft", "msedge", "msteams", "onedrive", "outlook",
        "skype", "cortana", "teams", "onenote", "excel", "word",
        "powerpoint", "office", "msaccess", "mspub", "lync",
        "todo", "whiteboard", "clipchamp",
    }

    # Never kill ourselves
    SELF_NAMES = {"powerpilot.exe", "python.exe", "pythonw.exe"}

    def __init__(self):
        self._processes = {}      # pid -> ProcessInfo
        self._username_cache = {} # pid -> username
        self._lock = threading.Lock()
        self._own_pid = os.getpid()
        self._scan_complete = False
        self._killed_pids = {}    # pid -> process name (for restore tracking)

    def _categorize_process(self, name_lower):
        """Categorize a process by its executable name.

        Args:
            name_lower: Lowercase process name.

        Returns:
            tuple: (category, is_mandatory, description).
        """
        # Check mandatory first
        if name_lower in self.MANDATORY_PROCESSES:
            return "windows", True, "Critical system process"

        # Check known Windows background processes
        if name_lower in self.WINDOWS_BG_PROCESSES:
            return "windows", False, self.WINDOWS_BG_PROCESSES[name_lower]

        # Check Microsoft identifiers
        for ident in self.MICROSOFT_IDENTIFIERS:
            if ident in name_lower:
                return "microsoft", False, "Microsoft application"

        return "third_party", False, ""

    def _is_system_account(self, proc, pid):
        """Check if a process runs under a system/service account.

        Args:
            proc: psutil.Process instance.
            pid: Process ID.

        Returns:
            bool: True if it's a system/service account process.
        """
        username = self._username_cache.get(pid)
        if username is None:
            try:
                username = proc.username() or ""
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                username = ""
            self._username_cache[pid] = username

        if username:
            upper = username.upper()
            return any(
                s in upper
                for s in ["SYSTEM", "LOCAL SERVICE", "NETWORK SERVICE",
                          "UMFD-", "DWM-"]
            )
        return False

    def scan_all_processes(self):
        """Scan all running processes and categorize them.

        Returns:
            int: Total number of processes found.
        """
        current_pids = set()

        # High-performance query: avoid querying slow Windows service status
        for proc in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_info"]
        ):
            try:
                pid = proc.info["pid"]
                name = proc.info.get("name", "")
                if not name or pid <= 4:
                    continue

                name_lower = name.lower()

                # Skip ourselves
                if name_lower in self.SELF_NAMES or pid == self._own_pid:
                    continue

                current_pids.add(pid)

                mem_info = proc.info.get("memory_info")
                memory_mb = (
                    round(mem_info.rss / (1024 * 1024), 1) if mem_info else 0
                )

                category, is_mandatory, description = self._categorize_process(
                    name_lower
                )

                # System-account processes in non-mandatory list get
                # a mandatory flag to prevent accidental termination
                if not is_mandatory and self._is_system_account(proc, pid):
                    is_mandatory = True
                    description = description or "System service"

                proc_info = ProcessInfo(
                    pid=pid,
                    name=name,
                    cpu_percent=proc.info.get("cpu_percent", 0) or 0,
                    memory_mb=memory_mb,
                    status="running",
                    category=category,
                    is_mandatory=is_mandatory,
                    description=description,
                )

                with self._lock:
                    # Preserve user toggle state if we already tracked this pid
                    if pid in self._processes:
                        proc_info.is_enabled = self._processes[pid].is_enabled
                    self._processes[pid] = proc_info

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Remove dead processes
        with self._lock:
            dead = set(self._processes.keys()) - current_pids
            for pid in dead:
                del self._processes[pid]
            dead_users = set(self._username_cache.keys()) - current_pids
            for pid in dead_users:
                self._username_cache.pop(pid, None)

        self._scan_complete = True
        return len(current_pids)

    def is_scan_complete(self):
        """Check if at least one full scan has completed."""
        return self._scan_complete

    def get_all_processes(self):
        """Return all scanned processes as a list of ProcessInfo.

        Returns:
            list[ProcessInfo]: All processes sorted by memory usage descending.
        """
        with self._lock:
            return sorted(
                self._processes.values(),
                key=lambda p: p.memory_mb,
                reverse=True,
            )

    def get_processes_by_category(self, category):
        """Get processes filtered by category.

        Args:
            category: One of 'windows', 'microsoft', 'third_party'.

        Returns:
            list[ProcessInfo]: Filtered process list.
        """
        with self._lock:
            return sorted(
                [p for p in self._processes.values() if p.category == category],
                key=lambda p: p.memory_mb,
                reverse=True,
            )

    def get_non_mandatory_processes(self):
        """Get all processes that can be safely terminated.

        Returns:
            list[ProcessInfo]: Non-mandatory processes.
        """
        with self._lock:
            return sorted(
                [p for p in self._processes.values() if not p.is_mandatory],
                key=lambda p: p.memory_mb,
                reverse=True,
            )

    def get_category_stats(self):
        """Get stats per category.

        Returns:
            dict: Category -> {'count': int, 'memory_mb': float, 'killable': int}.
        """
        stats = {}
        with self._lock:
            for proc in self._processes.values():
                cat = proc.category
                if cat not in stats:
                    stats[cat] = {"count": 0, "memory_mb": 0.0, "killable": 0}
                stats[cat]["count"] += 1
                stats[cat]["memory_mb"] += proc.memory_mb
                if not proc.is_mandatory:
                    stats[cat]["killable"] += 1
        # Round memory values
        for cat in stats:
            stats[cat]["memory_mb"] = round(stats[cat]["memory_mb"], 1)
        return stats

    def kill_process(self, pid):
        """Terminate a single process.

        Args:
            pid: Process ID to kill.

        Returns:
            bool: True if successfully killed.
        """
        if pid == self._own_pid:
            return False

        with self._lock:
            proc_info = self._processes.get(pid)
            if proc_info and proc_info.is_mandatory:
                return False

        try:
            proc = psutil.Process(pid)
            proc_name = proc.name()
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                proc.kill()

            self._killed_pids[pid] = proc_name
            with self._lock:
                self._processes.pop(pid, None)
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            with self._lock:
                self._processes.pop(pid, None)
            return False

    def kill_all_non_mandatory(self, category=None):
        """Kill all non-mandatory processes, optionally filtered by category.

        Args:
            category: If specified, only kill processes in this category.

        Returns:
            int: Number of processes killed.
        """
        with self._lock:
            targets = [
                p.pid for p in self._processes.values()
                if not p.is_mandatory and p.pid != self._own_pid
                and (category is None or p.category == category)
            ]

        if not targets:
            return 0

        # Fast path: Native C# parallel termination
        if NATIVE_EXE.exists():
            try:
                pid_str = ",".join(str(p) for p in targets)
                res = subprocess.run([str(NATIVE_EXE), "kill-pids", pid_str], capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
                if res and res.stdout:
                    data = json.loads(res.stdout.strip())
                    self.scan_all_processes()
                    return data.get("killed", 0)
            except Exception:
                pass

        killed = 0
        # Phase 1: Graceful termination
        for pid in targets:
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        time.sleep(2)

        # Phase 2: Force kill survivors
        for pid in targets:
            try:
                proc = psutil.Process(pid)
                if proc.is_running():
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Refresh
        self.scan_all_processes()
        return killed

    def kill_windows_background(self):
        """Kill all non-mandatory Windows/Microsoft background processes.

        Returns:
            int: Number of processes killed.
        """
        killed_w = self.kill_all_non_mandatory(category="windows")
        killed_m = self.kill_all_non_mandatory(category="microsoft")
        return killed_w + killed_m

    def get_total_count(self):
        """Get total count of tracked processes."""
        with self._lock:
            return len(self._processes)

    def get_potential_savings_mb(self, category=None):
        """Estimate memory that could be freed by killing non-mandatory processes.

        Args:
            category: If specified, only count this category.

        Returns:
            float: Estimated memory savings in MB.
        """
        with self._lock:
            total = sum(
                p.memory_mb for p in self._processes.values()
                if not p.is_mandatory
                and (category is None or p.category == category)
            )
        return round(total, 1)
