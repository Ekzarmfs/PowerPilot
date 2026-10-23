"""
Process tracking module for PowerPilot.
Tracks user-started processes and provides one-click cleanup (Clean Sweep).
"""

import psutil
import os
import time
import threading
import ctypes
from ctypes import wintypes
import subprocess
import json
from pathlib import Path

NATIVE_EXE = Path(__file__).parent / "PowerPilotNative.exe"


class ProcessTracker:
    """Tracks running processes categorized into Active Apps, Background, and System,
    with real-time battery power drain percentage calculation and Clean Sweep cleanup."""

    # System/service processes that should never be terminated
    SYSTEM_PROCESSES = {
        "system",
        "system idle process",
        "registry",
        "smss.exe",
        "csrss.exe",
        "wininit.exe",
        "services.exe",
        "lsass.exe",
        "svchost.exe",
        "fontdrvhost.exe",
        "dwm.exe",
        "winlogon.exe",
        "logonui.exe",
        "sihost.exe",
        "taskhostw.exe",
        "explorer.exe",
        "shellexperiencehost.exe",
        "searchhost.exe",
        "startmenuexperiencehost.exe",
        "runtimebroker.exe",
        "textinputhost.exe",
        "ctfmon.exe",
        "securityhealthservice.exe",
        "securityhealthsystray.exe",
        "sgrmbroker.exe",
        "spoolsv.exe",
        "audiodg.exe",
        "searchindexer.exe",
        "searchprotocolhost.exe",
        "searchfilterhost.exe",
        "wmiprvse.exe",
        "dashost.exe",
        "conhost.exe",
        "dllhost.exe",
        "taskmgr.exe",
        "applicationframehost.exe",
        "lockapp.exe",
        "widgetservice.exe",
        "widgets.exe",
        "msedgewebview2.exe",
        "smartscreen.exe",
        "usoclient.exe",
        "musnotification.exe",
        "backgroundtaskhost.exe",
        "systemsettings.exe",
        "openssh-agent.exe",
        "wudfhost.exe",
        "unsecapp.exe",
        "msdtc.exe",
        "lsaiso.exe",
        "memory compression",
        "secure system",
        "gamebarpresencewriter.exe",
        "gamebarftserver.exe",
        "ntoskrnl.exe",
        "idle",
        "csrss",
        "wlanext.exe",
        "nvcontainer.exe",
        "igfxem.exe",
        "igfxhk.exe",
        "igfxtray.exe",
    }

    # Never kill ourselves
    SELF_NAMES = {"powerpilot.exe", "python.exe", "pythonw.exe"}

    def __init__(self):
        self._tracked = {}  # pid -> process info dict
        self._section_stats = {
            "active_apps": {"count": 0, "memory_mb": 0.0, "power_percent": 0.0},
            "background": {"count": 0, "memory_mb": 0.0, "power_percent": 0.0},
            "system": {"count": 0, "memory_mb": 0.0, "power_percent": 0.0},
            "top_consumer": None,
        }
        self._boot_time = psutil.boot_time()
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._excluded = set()
        self._own_pid = os.getpid()
        self._username_cache = {}  # pid -> username string

    def set_excluded(self, excluded_names):
        """Set additional process names to exclude from tracking.

        Args:
            excluded_names: Iterable of process name strings.
        """
        self._excluded = {name.lower() for name in excluded_names}

    def _get_active_window_pids(self):
        """Detect top-level interactive user windows currently open on desktop (in-process Win32 ~1.6ms).

        Returns:
            dict: Mapping of PID -> window title string.
        """
        active_map = {}
        try:
            user32 = ctypes.windll.user32

            # Open current input desktop or WinSta0
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
            if not hdesk:
                hwinsta = user32.OpenWindowStationW("WinSta0", False, 0x037F)
                if hwinsta:
                    user32.SetProcessWindowStation(hwinsta)
                    hdesk = user32.OpenDesktopW("default", 0, False, 0x01FF)

            if not hdesk:
                return active_map

            class _RECT(ctypes.Structure):
                _fields_ = [
                    ("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long),
                ]

            def _enum_cb(hwnd, lparam):
                if not user32.IsWindowVisible(hwnd):
                    return True

                rect = _RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                if w <= 16 or h <= 16:
                    return True

                length = user32.GetWindowTextLengthW(hwnd)
                if length <= 0:
                    return True

                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value.strip()

                if not title or title in (
                    "Default IME",
                    "MSCTFIME UI",
                    "Program Manager",
                    "Windows Shell Experience Host",
                    "Battery Optimizer",
                ):
                    return True

                # Exclude tool windows (floating utility panels, tray tips)
                ex_style = user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
                if ex_style & 0x00000080:  # WS_EX_TOOLWINDOW
                    return True

                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value > 0 and pid.value not in active_map:
                    active_map[pid.value] = title

                return True

            _WNDENUMPROC = ctypes.WINFUNCTYPE(
                wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
            )
            user32.EnumDesktopWindows(hdesk, _WNDENUMPROC(_enum_cb), 0)
            user32.CloseDesktop(hdesk)
        except Exception:
            pass

        return active_map

    def _is_system_process(self, proc, name_lower, pid):
        """Check if a process is a Windows core system service or infrastructure.

        Args:
            proc: psutil.Process instance.
            name_lower: Lowercase process name.
            pid: Process ID.

        Returns:
            bool: True if process is a system service.
        """
        if pid <= 4 or name_lower in self.SYSTEM_PROCESSES:
            return True

        username = self._username_cache.get(pid)
        if username is None:
            try:
                username = proc.username()
                self._username_cache[pid] = username or ""
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                self._username_cache[pid] = ""
                username = ""

        if username:
            upper = username.upper()
            if any(
                s in upper
                for s in [
                    "SYSTEM",
                    "LOCAL SERVICE",
                    "NETWORK SERVICE",
                    "UMFD-",
                    "DWM-",
                ]
            ):
                return True

        return False

    def scan_processes(self):
        """Scan running processes, categorize into 3 sections, and compute battery power %."""
        current_pids = set()
        active_windows = self._get_active_window_pids()
        scanned_list = []

        # High-performance scan: only query pid, name, cpu_percent, memory_info
        for proc in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_info"]
        ):
            try:
                pid = proc.info["pid"]
                name = proc.info.get("name") or "Unknown"
                name_lower = name.lower()

                # Always skip PID 0 (System Idle Process) and our own PID from being managed/killed
                if pid == 0 or pid == self._own_pid or name_lower in ("system idle process", "idle"):
                    continue

                current_pids.add(pid)

                mem_info = proc.info.get("memory_info")
                memory_mb = (
                    round(mem_info.rss / (1024 * 1024), 1) if mem_info else 0.0
                )
                cpu_percent = proc.info.get("cpu_percent", 0.0) or 0.0
                create_time = 0.0
                status = "running"

                # Section Classification:
                # 1. Active Apps: User opened with visible desktop window
                # 2. Background: User/third-party apps running without visible window
                # 3. System: Core Windows services, daemons, and system infrastructure
                is_system = self._is_system_process(proc, name_lower, pid)

                if pid in active_windows and not is_system:
                    section = "active_apps"
                    window_title = active_windows[pid]
                    is_user = True
                    is_killable = True
                elif is_system:
                    section = "system"
                    window_title = ""
                    is_user = False
                    is_killable = False
                else:
                    section = "background"
                    window_title = ""
                    is_user = True
                    is_killable = True

                # Battery Power Raw Drain Score:
                # CPU is the primary dynamic consumer of CPU package power (watts).
                # Active foreground apps draw additional display composite power.
                # RAM footprint requires periodic DRAM refresh cycles.
                cpu_score = max(0.0, cpu_percent) * 1.5
                mem_score = min(10.0, memory_mb / 160.0)
                active_bonus = 2.0 if (section == "active_apps" and cpu_score > 0.0) else 0.0
                raw_power = cpu_score + mem_score + active_bonus

                scanned_list.append({
                    "pid": pid,
                    "name": name,
                    "window_title": window_title,
                    "section": section,
                    "is_user": is_user,
                    "is_killable": is_killable,
                    "cpu_percent": round(cpu_percent, 1),
                    "memory_mb": memory_mb,
                    "raw_power": raw_power,
                    "create_time": create_time,
                    "status": status,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Compute relative power percentages
        total_raw = sum(p["raw_power"] for p in scanned_list)
        active_raw = sum(p["raw_power"] for p in scanned_list if p["section"] == "active_apps")

        stats = {
            "active_apps": {"count": 0, "memory_mb": 0.0, "power_percent": 0.0},
            "background": {"count": 0, "memory_mb": 0.0, "power_percent": 0.0},
            "system": {"count": 0, "memory_mb": 0.0, "power_percent": 0.0},
            "top_consumer": None,
        }

        updated_tracked = {}
        for p in scanned_list:
            raw = p["raw_power"]
            pct = round((raw / total_raw) * 100.0, 1) if total_raw > 0 else 0.0
            p["power_percent"] = pct

            if p["section"] == "active_apps" and active_raw > 0:
                p["active_power_percent"] = round((raw / active_raw) * 100.0, 1)
            else:
                p["active_power_percent"] = 0.0

            # Power Level badge classification
            if pct >= 25.0:
                p["power_level"] = "Very High"
                p["power_color"] = "#f85149"
            elif pct >= 12.0:
                p["power_level"] = "High"
                p["power_color"] = "#ff9800"
            elif pct >= 4.0:
                p["power_level"] = "Moderate"
                p["power_color"] = "#e3b341"
            else:
                p["power_level"] = "Low"
                p["power_color"] = "#3fb950"

            # Aggregate section stats
            sec = p["section"]
            stats[sec]["count"] += 1
            stats[sec]["memory_mb"] = round(stats[sec]["memory_mb"] + p["memory_mb"], 1)
            stats[sec]["power_percent"] = round(stats[sec]["power_percent"] + pct, 1)

            updated_tracked[p["pid"]] = p

        # Find top power consumer
        if scanned_list:
            top_p = max(scanned_list, key=lambda x: x["power_percent"])
            if top_p["power_percent"] > 0.0:
                stats["top_consumer"] = {
                    "name": top_p["name"],
                    "window_title": top_p["window_title"],
                    "pid": top_p["pid"],
                    "power_percent": top_p["power_percent"],
                    "section": top_p["section"],
                }

        with self._lock:
            self._tracked = updated_tracked
            self._section_stats = stats
            # Clean username cache for dead pids
            dead_pids = set(self._username_cache.keys()) - current_pids
            for d in dead_pids:
                self._username_cache.pop(d, None)

    def get_processes(self, section=None):
        """Get list of tracked processes, optionally filtered by section.

        Args:
            section: Optional string filter ("active_apps", "background", "system").

        Returns:
            list[dict]: List of process info dicts sorted by battery power drain.
        """
        with self._lock:
            procs = list(self._tracked.values())

        if section:
            procs = [p for p in procs if p.get("section") == section]

        return sorted(procs, key=lambda p: p["power_percent"], reverse=True)

    def get_processes_by_section(self):
        """Get processes partitioned by their 3 sections.

        Returns:
            dict: {"active_apps": [...], "background": [...], "system": [...]}
        """
        with self._lock:
            procs = list(self._tracked.values())

        grouped = {"active_apps": [], "background": [], "system": []}
        for p in procs:
            sec = p.get("section", "system")
            if sec in grouped:
                grouped[sec].append(p)
            else:
                grouped["system"].append(p)

        for sec in grouped:
            grouped[sec].sort(key=lambda p: p["power_percent"], reverse=True)

        return grouped

    def get_section_stats(self):
        """Get aggregate metrics and power breakdown for all 3 sections."""
        with self._lock:
            return dict(self._section_stats)

    def get_top_power_consumers(self, limit=5):
        """Get the top battery-draining processes across the system."""
        with self._lock:
            procs = list(self._tracked.values())
        procs.sort(key=lambda p: p["power_percent"], reverse=True)
        return procs[:limit]

    def get_user_processes(self):
        """Get all user-started processes (Active Apps + Background)."""
        with self._lock:
            return [p for p in self._tracked.values() if p.get("is_user", False)]

    def get_process_count(self, section=None):
        """Get count of processes (user processes by default, or filtered by section)."""
        with self._lock:
            if section:
                return len([p for p in self._tracked.values() if p.get("section") == section])
            return len([p for p in self._tracked.values() if p.get("is_user", False)])

    def get_total_count(self):
        """Get count of all tracked processes across all sections."""
        with self._lock:
            return len(self._tracked)

    def get_total_memory_mb(self, section=None):
        """Get total memory usage of processes in MB."""
        with self._lock:
            if section:
                return round(sum(p["memory_mb"] for p in self._tracked.values() if p.get("section") == section), 1)
            return round(sum(p["memory_mb"] for p in self._tracked.values() if p.get("is_user", False)), 1)

    def get_process_details(self, pid):
        """Get rich inspection details for a single process.

        Args:
            pid: Process ID to inspect.

        Returns:
            dict or None: Detailed dictionary of process metrics.
        """
        try:
            p = psutil.Process(pid)
            with p.oneshot():
                name = p.name()
                try:
                    exe = p.exe()
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    exe = "Access Denied / Protected"
                try:
                    cmdline = " ".join(p.cmdline())
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    cmdline = "N/A"
                try:
                    threads = p.num_threads()
                except Exception:
                    threads = 0
                try:
                    create_time = p.create_time()
                except Exception:
                    create_time = 0
                try:
                    mem_info = p.memory_info()
                    mem_mb = round(mem_info.rss / (1024 * 1024), 1)
                except Exception:
                    mem_mb = 0
                try:
                    mem_percent = round(p.memory_percent(), 1)
                except Exception:
                    mem_percent = 0.0
                try:
                    cpu = p.cpu_percent(interval=None)
                except Exception:
                    cpu = 0.0
                try:
                    status = p.status()
                except Exception:
                    status = "unknown"
                try:
                    username = p.username()
                except Exception:
                    username = self._username_cache.get(pid, "N/A")
                try:
                    parent = p.parent()
                    parent_name = f"{parent.name()} ({parent.pid})" if parent else "None"
                except Exception:
                    parent_name = "N/A"

            # Retrieve window title and power metrics if available
            with self._lock:
                tracked_info = self._tracked.get(pid, {})

            return {
                "pid": pid,
                "name": name,
                "window_title": tracked_info.get("window_title", ""),
                "section": tracked_info.get("section", "unknown"),
                "power_percent": tracked_info.get("power_percent", 0.0),
                "power_level": tracked_info.get("power_level", "Low"),
                "exe": exe,
                "cmdline": cmdline,
                "threads": threads,
                "create_time": create_time,
                "memory_mb": mem_mb,
                "memory_percent": mem_percent,
                "cpu_percent": cpu,
                "status": status,
                "username": username,
                "parent": parent_name,
                "is_killable": tracked_info.get("is_killable", True),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    def kill_process(self, pid):
        """Kill a single process by PID, safely skipping protected/system processes.

        Args:
            pid: Process ID to terminate.

        Returns:
            bool: True if the process was successfully killed.
        """
        if pid == self._own_pid:
            return False

        with self._lock:
            p_info = self._tracked.get(pid)
            if p_info and not p_info.get("is_killable", True):
                return False

        try:
            proc = psutil.Process(pid)
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except psutil.TimeoutExpired:
                proc.kill()

            with self._lock:
                self._tracked.pop(pid, None)
                self._username_cache.pop(pid, None)
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            with self._lock:
                self._tracked.pop(pid, None)
                self._username_cache.pop(pid, None)
            return False

    def clean_sweep(self, progress_callback=None):
        """Kill all tracked user processes (Active Apps + Background non-system processes).
        System processes and PowerPilot itself are completely protected.

        Args:
            progress_callback: Optional callable(status_text) for progress reporting.

        Returns:
            int: Number of processes successfully terminated.
        """
        killed = 0
        with self._lock:
            pids_to_kill = [
                pid
                for pid, p in self._tracked.items()
                if p.get("is_user", False)
                and p.get("is_killable", True)
                and pid != self._own_pid
            ]

        total = len(pids_to_kill)
        if total == 0:
            return 0

        if progress_callback:
            progress_callback(f"Gracefully terminating {total} processes...")

        # Fast path: Native C# parallel termination
        if NATIVE_EXE.exists():
            try:
                pid_str = ",".join(str(p) for p in pids_to_kill)
                res = subprocess.run([str(NATIVE_EXE), "kill-pids", pid_str], capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
                if res and res.stdout:
                    data = json.loads(res.stdout.strip())
                    killed = data.get("killed", 0)
                    if progress_callback:
                        progress_callback("Updating process inventory...")
                    self.scan_processes()
                    return killed
            except Exception:
                pass

        # Fallback Phase 1: Graceful termination via psutil
        survivors = []
        for i, pid in enumerate(pids_to_kill):
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                survivors.append(proc)
                killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Wait for processes to exit (poll up to 1.5 seconds)
        if survivors:
            _, alive = psutil.wait_procs(survivors, timeout=1.5)
            # Phase 2: Force kill remaining alive processes
            if alive:
                if progress_callback:
                    progress_callback(f"Force closing {len(alive)} remaining processes...")
                for proc in alive:
                    try:
                        proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

        if progress_callback:
            progress_callback("Updating process inventory...")

        # Refresh the process list
        self.scan_processes()
        return killed

    def start_tracking(self, interval=3):
        """Start periodic process scanning in background.

        Args:
            interval: Seconds between scans (default 3).
        """
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._track_loop, args=(interval,), daemon=True
        )
        self._thread.start()

    def stop_tracking(self):
        """Stop the background process tracking."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _track_loop(self, interval):
        """Internal tracking loop running in background thread."""
        while self._running:
            self.scan_processes()
            time.sleep(interval)
