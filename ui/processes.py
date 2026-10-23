"""
Process Tracker and Relative Battery Drain View for PowerPilot.
Implements precision 3-tier process monitoring (Active Applications,
Background Processes, System Services) with live relative battery drain (%),
interactive inspection, Clean Sweep utility, zero-tearing geometry, and
buttery-smooth scrolling.
"""

from collections import defaultdict
import os
import subprocess
import threading
import time
import customtkinter as ctk

from ui.theme import Colors, Fonts, Dimensions, get_drain_color_tuple


class ProcessDetailsDialog(ctk.CTkToplevel):
    """Detailed inspection dialog for a running process."""

    def __init__(self, master, proc_details, on_kill=None, **kwargs):
        super().__init__(master, **kwargs)

        self._details = proc_details
        self._on_kill = on_kill
        self._pid = proc_details.get("pid", 0)

        self.title(f"Process Details — PID {self._pid}")
        self.geometry("520x440")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_PRIMARY)

        # Modal behavior
        self.transient(master.winfo_toplevel())
        self.grab_set()

        self._build_ui()

        # Center on parent window
        self.after(10, self._center_window)

    def _center_window(self):
        try:
            self.update_idletasks()
            pw = self.master.winfo_toplevel()
            x = pw.winfo_x() + (pw.winfo_width() - self.winfo_width()) // 2
            y = pw.winfo_y() + (pw.winfo_height() - self.winfo_height()) // 2
            self.geometry(f"+{max(10, x)}+{max(10, y)}")
        except Exception:
            pass

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Header with name and PID
        name = self._details.get("name", "Unknown Process")
        wtitle = self._details.get("window_title", "")
        primary_title = wtitle if wtitle else name

        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(
            header,
            text=primary_title,
            font=Fonts.HEADING_2,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x")

        sub_text = f"{name}  •  PID {self._pid}"
        if self._details.get("is_user"):
            sub_text += "  •  User Process"
        else:
            sub_text += "  •  System Process (Protected)"

        ctk.CTkLabel(
            header,
            text=sub_text,
            font=Fonts.CAPTION,
            text_color=Colors.TEXT_TERTIARY,
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        # Metrics overview bar
        metrics_bar = ctk.CTkFrame(
            container,
            fg_color=Colors.BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER,
        )
        metrics_bar.pack(fill="x", pady=(0, 14))
        metrics_bar.grid_columnconfigure((0, 1, 2), weight=1)

        pwr = self._details.get("power_percent", 0.0)
        pwr_text = f"⚡ {pwr:.1f}%" if pwr > 0 else "< 0.1%"
        self._add_metric_chip(metrics_bar, 0, "BATTERY DRAIN", pwr_text, Colors.ACCENT)

        cpu = self._details.get("cpu_percent", 0.0)
        self._add_metric_chip(metrics_bar, 1, "CPU USAGE", f"{cpu:.1f}%", Colors.WARNING if cpu > 20 else Colors.TEXT_PRIMARY)

        mem = self._details.get("memory_mb", 0.0)
        mem_text = f"{mem:.1f} MB" if mem < 1024 else f"{mem / 1024:.2f} GB"
        self._add_metric_chip(metrics_bar, 2, "MEMORY", mem_text, Colors.TEXT_PRIMARY)

        # Details list card
        details_card = ctk.CTkFrame(
            container,
            fg_color=Colors.BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER,
        )
        details_card.pack(fill="both", expand=True, pady=(0, 14))

        inner = ctk.CTkFrame(details_card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14, pady=12)

        created_str = "Unknown"
        ct = self._details.get("create_time")
        if ct:
            try:
                created_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ct))
            except Exception:
                pass

        fields = [
            ("Executable Path", self._details.get("exe") or "Protected / Unavailable"),
            ("Username / Account", self._details.get("username") or "System / Local"),
            ("Status", str(self._details.get("status", "running")).capitalize()),
            ("Thread Count", str(self._details.get("num_threads", 0))),
            ("Process Section", self._details.get("section", "Background").title()),
            ("Started At", created_str),
        ]

        for i, (lbl, val) in enumerate(fields):
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(
                row,
                text=lbl,
                font=Fonts.CAPTION_BOLD,
                text_color=Colors.TEXT_TERTIARY,
                width=130,
                anchor="w",
            ).pack(side="left")

            val_label = ctk.CTkLabel(
                row,
                text=val,
                font=Fonts.CAPTION,
                text_color=Colors.TEXT_PRIMARY,
                anchor="w",
            )
            val_label.pack(side="left", fill="x", expand=True)

        # Action Buttons footer
        btn_bar = ctk.CTkFrame(container, fg_color="transparent")
        btn_bar.pack(fill="x")

        # Open in Explorer
        exe = self._details.get("exe")
        if exe and os.path.exists(exe):
            ctk.CTkButton(
                btn_bar,
                text="📁 Open Location",
                font=Fonts.BODY_SMALL,
                fg_color=Colors.BG_CARD,
                hover_color=Colors.BG_CARD_HOVER,
                text_color=Colors.TEXT_PRIMARY,
                border_width=1,
                border_color=Colors.BORDER,
                height=34,
                corner_radius=6,
                command=self._open_location,
            ).pack(side="left")

        # Close button
        ctk.CTkButton(
            btn_bar,
            text="Close",
            font=Fonts.BODY_SMALL,
            fg_color=Colors.BG_CARD,
            hover_color=Colors.BG_CARD_HOVER,
            text_color=Colors.TEXT_SECONDARY,
            border_width=1,
            border_color=Colors.BORDER,
            height=34,
            width=80,
            corner_radius=6,
            command=self.destroy,
        ).pack(side="right")

        # Kill Process button
        is_killable = self._details.get("is_killable", True)
        if is_killable:
            ctk.CTkButton(
                btn_bar,
                text="✕ Terminate Process",
                font=Fonts.BODY_BOLD,
                fg_color=Colors.DANGER,
                hover_color=Colors.DANGER_HOVER,
                text_color=Colors.TEXT_PRIMARY,
                height=34,
                corner_radius=6,
                command=self._confirm_kill,
            ).pack(side="right", padx=(0, 8))

    def _add_metric_chip(self, parent, col, label, value, color):
        chip = ctk.CTkFrame(parent, fg_color="transparent")
        chip.grid(row=0, column=col, padx=8, pady=8, sticky="ew")

        ctk.CTkLabel(
            chip,
            text=label,
            font=Fonts.TINY,
            text_color=Colors.TEXT_TERTIARY,
            anchor="center",
        ).pack()

        ctk.CTkLabel(
            chip,
            text=value,
            font=Fonts.BODY_BOLD,
            text_color=color,
            anchor="center",
        ).pack(pady=(2, 0))

    def _open_location(self):
        exe = self._details.get("exe")
        if exe and os.path.exists(exe):
            try:
                subprocess.Popen(f'explorer.exe /select,"{os.path.normpath(exe)}"')
            except Exception:
                pass

    def _confirm_kill(self):
        self.destroy()
        if self._on_kill:
            self._on_kill(self._pid)


class ConfirmActionDialog(ctk.CTkToplevel):
    """Reusable, sleek confirmation dialog for destructive actions."""

    def __init__(self, master, title, heading, message, confirm_text, on_confirm, confirm_color=None):
        super().__init__(master)
        self.title(title)
        self.geometry("420x210")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_PRIMARY)
        self.transient(master.winfo_toplevel())
        self.grab_set()

        try:
            self.update_idletasks()
            pw = master.winfo_toplevel()
            x = pw.winfo_x() + (pw.winfo_width() - 420) // 2
            y = pw.winfo_y() + (pw.winfo_height() - 210) // 2
            self.geometry(f"+{max(10, x)}+{max(10, y)}")
        except Exception:
            pass

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=18)

        ctk.CTkLabel(inner, text=heading, font=Fonts.HEADING_2, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(inner, text=message, font=Fonts.CAPTION, text_color=Colors.TEXT_SECONDARY, justify="left", wraplength=380).pack(anchor="w", pady=(8, 14))

        btn_bar = ctk.CTkFrame(inner, fg_color="transparent")
        btn_bar.pack(fill="x")

        ctk.CTkButton(
            btn_bar, text="Cancel", font=Fonts.BODY_SMALL,
            fg_color=Colors.BG_CARD, hover_color=Colors.BG_CARD_HOVER,
            text_color=Colors.TEXT_SECONDARY, border_width=1, border_color=Colors.BORDER,
            width=80, height=32, corner_radius=6, command=self.destroy,
        ).pack(side="left")

        def _confirm():
            self.destroy()
            on_confirm()

        ctk.CTkButton(
            btn_bar, text=confirm_text, font=Fonts.BODY_BOLD,
            fg_color=confirm_color or Colors.DANGER, hover_color=Colors.DANGER_HOVER,
            text_color=Colors.TEXT_PRIMARY, height=32, corner_radius=6, command=_confirm,
        ).pack(side="right")


def aggregate_processes(processes, is_dict=True):
    """Aggregate duplicate instances of system/service processes.

    Supports both dictionary objects (used in ProcessTracker) and ProcessInfo objects
    (used in BackgroundProcessManager).
    """
    grouped = defaultdict(list)
    for p in processes:
        name = p["name"] if is_dict else p.name
        grouped[name.lower()].append(p)

    aggregated = []
    for name_lower, p_list in grouped.items():
        if len(p_list) == 1:
            aggregated.append(p_list[0])
        else:
            count = len(p_list)
            first = p_list[0]
            if is_dict:
                tot_mem = round(sum(p.get("memory_mb", 0.0) for p in p_list), 1)
                tot_cpu = round(sum(p.get("cpu_percent", 0.0) for p in p_list), 1)
                tot_pwr = round(sum(p.get("power_percent", 0.0) for p in p_list), 1)
                agg = dict(first)
                agg["name"] = f"{first['name']} ({count} instances)"
                agg["memory_mb"] = tot_mem
                agg["cpu_percent"] = tot_cpu
                agg["power_percent"] = tot_pwr
                agg["is_killable"] = False
                aggregated.append(agg)
            else:
                from core.bg_process_manager import ProcessInfo
                tot_mem = round(sum(p.memory_mb for p in p_list), 1)
                tot_cpu = round(sum(p.cpu_percent for p in p_list), 1)
                agg = ProcessInfo(
                    pid=first.pid,
                    name=f"{first.name} ({count} instances)",
                    cpu_percent=tot_cpu,
                    memory_mb=tot_mem,
                    status="running",
                    category=first.category,
                    is_mandatory=True,
                    description=first.description or "Critical system services",
                )
                aggregated.append(agg)
    return aggregated


def configure_process_columns(frame):
    """Enforce strict uniform column widths across all rows and the header."""
    frame.grid_columnconfigure(0, weight=36, uniform="proc_cols")  # App / Process Name
    frame.grid_columnconfigure(1, weight=10, uniform="proc_cols")  # PID
    frame.grid_columnconfigure(2, weight=18, uniform="proc_cols")  # ⚡ Battery Drain %
    frame.grid_columnconfigure(3, weight=11, uniform="proc_cols")  # CPU
    frame.grid_columnconfigure(4, weight=12, uniform="proc_cols")  # Memory
    frame.grid_columnconfigure(5, weight=13, uniform="proc_cols")  # Actions


class ProcessRow(ctk.CTkFrame):
    """A lightweight, zero-tearing process row with laser-aligned columns.
    Uses uniform column weights so every label starts at the exact same horizontal position."""

    def __init__(self, master, proc_data, on_kill, on_inspect, **kwargs):
        super().__init__(
            master,
            fg_color=Colors.BG_CARD,
            corner_radius=6,
            cursor="hand2",
            **kwargs,
        )

        self._pid = proc_data["pid"]
        self._proc_data = proc_data
        self._on_kill = on_kill
        self._on_inspect = on_inspect
        self._is_hovered = False

        self._cpu = -1.0
        self._mem = -1.0
        self._pwr = -1.0

        # Uniform 6-column grid layout
        configure_process_columns(self)

        # Col 0: App Name + Subtitle (PID & exe) — left-aligned
        name_container = ctk.CTkFrame(self, fg_color="transparent", cursor="hand2")
        name_container.grid(row=0, column=0, sticky="ew", padx=(16, 8), pady=5)

        self._primary_label = ctk.CTkLabel(
            name_container,
            text="",
            font=Fonts.BODY_BOLD,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
            cursor="hand2",
        )
        self._primary_label.pack(fill="x", anchor="w")

        self._sub_label = ctk.CTkLabel(
            name_container,
            text="",
            font=Fonts.TINY,
            text_color=Colors.TEXT_TERTIARY,
            anchor="w",
            cursor="hand2",
        )
        self._sub_label.pack(fill="x", anchor="w")

        # Col 1: PID — left-aligned at exact column start
        self._pid_label = ctk.CTkLabel(
            self,
            text=str(proc_data["pid"]),
            font=Fonts.CAPTION,
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            cursor="hand2",
        )
        self._pid_label.grid(row=0, column=1, sticky="ew", padx=(10, 8), pady=5)

        # Col 2: Battery Drain % (Pill) — left-aligned at exact column start
        pwr_box = ctk.CTkFrame(self, fg_color="transparent", cursor="hand2")
        pwr_box.grid(row=0, column=2, sticky="ew", padx=(10, 8), pady=5)

        self._pwr_badge = ctk.CTkLabel(
            pwr_box,
            text="⚡ 0.0%",
            font=Fonts.CAPTION_BOLD,
            text_color=Colors.TEXT_SECONDARY,
            fg_color=Colors.BG_ELEVATED,
            corner_radius=5,
            padx=8,
            pady=2,
            anchor="center",
            cursor="hand2",
        )
        self._pwr_badge.pack(side="left")

        # Col 3: CPU % — left-aligned at exact column start
        self._cpu_label = ctk.CTkLabel(
            self,
            text="0.0%",
            font=Fonts.CAPTION,
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            cursor="hand2",
        )
        self._cpu_label.grid(row=0, column=3, sticky="ew", padx=(10, 8), pady=5)

        # Col 4: Memory — left-aligned at exact column start
        self._mem_label = ctk.CTkLabel(
            self,
            text="0 MB",
            font=Fonts.CAPTION,
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            cursor="hand2",
        )
        self._mem_label.grid(row=0, column=4, sticky="ew", padx=(10, 8), pady=5)

        # Col 5: Actions — right-aligned
        btn_container = ctk.CTkFrame(self, fg_color="transparent")
        btn_container.grid(row=0, column=5, sticky="e", padx=(0, 16), pady=5)

        self._info_btn = ctk.CTkButton(
            btn_container,
            text="ⓘ",
            font=("Segoe UI", 11, "bold"),
            fg_color="transparent",
            hover_color=Colors.BG_ELEVATED,
            text_color=Colors.TEXT_SECONDARY,
            width=24,
            height=24,
            corner_radius=4,
            command=self._handle_inspect,
        )
        self._info_btn.pack(side="left", padx=(0, 4))

        is_killable = proc_data.get("is_killable", True)
        if is_killable:
            self._kill_btn = ctk.CTkButton(
                btn_container,
                text="✕ Stop",
                font=Fonts.CAPTION_BOLD,
                fg_color="transparent",
                hover_color=Colors.DANGER_BG,
                text_color=Colors.DANGER,
                border_width=1,
                border_color=Colors.BORDER,
                width=52,
                height=24,
                corner_radius=4,
                command=lambda: self._on_kill(self._pid),
            )
            self._kill_btn.pack(side="left")
        else:
            self._kill_btn = None
            ctk.CTkLabel(
                btn_container,
                text="🛡️",
                font=Fonts.CAPTION,
                text_color=Colors.TEXT_TERTIARY,
                width=24,
            ).pack(side="left")

        # Populate initial values
        self.update_data(proc_data)

        # Hover state - debounced and bounds-checked to avoid canvas redraw storms
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Double-Button-1>", lambda e: self._handle_inspect())
        for w in (name_container, self._primary_label, self._sub_label, self._pid_label,
                  pwr_box, self._pwr_badge, self._cpu_label, self._mem_label):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)
            w.bind("<Double-Button-1>", lambda e: self._handle_inspect())

    def _on_enter(self, event=None):
        if not self._is_hovered:
            self._is_hovered = True
            self.configure(fg_color=Colors.BG_CARD_HOVER)

    def _on_leave(self, event=None):
        try:
            x, y = self.winfo_pointerxy()
            rx = self.winfo_rootx()
            ry = self.winfo_rooty()
            w = self.winfo_width()
            h = self.winfo_height()
            if rx <= x <= rx + w and ry <= y <= ry + h:
                return  # Still inside row bounding box
        except Exception:
            pass
        if self._is_hovered:
            self._is_hovered = False
            self.configure(fg_color=Colors.BG_CARD)

    def _handle_inspect(self):
        if self._on_inspect:
            self._on_inspect(self._pid)

    def update_data(self, proc_data):
        """Update metrics in-place without destroying or repacking any widgets."""
        self._proc_data = proc_data

        # Window Title & Process Name
        wtitle = proc_data.get("window_title", "")
        name = proc_data.get("name", "Unknown")

        if wtitle and wtitle != name:
            # Interactive window: show window title in bold, exe name as subtitle
            truncated_title = wtitle if len(wtitle) <= 55 else wtitle[:52] + "..."
            self._primary_label.configure(text=truncated_title)
            self._sub_label.configure(text=f"{name}  •  PID {proc_data['pid']}")
        else:
            truncated_name = name if len(name) <= 45 else name[:42] + "..."
            self._primary_label.configure(text=truncated_name)
            self._sub_label.configure(text=f"PID {proc_data['pid']}")

        # Battery Power Drain %
        pwr = proc_data.get("power_percent", 0.0)
        if pwr != self._pwr:
            self._pwr = pwr
            txt_col, bg_col = get_drain_color_tuple(pwr)
            pwr_text = f"⚡ {pwr:.1f}%" if pwr > 0.0 else "< 0.1%"
            self._pwr_badge.configure(text=pwr_text, fg_color=bg_col, text_color=txt_col)

        # CPU %
        cpu = proc_data.get("cpu_percent", 0.0)
        if cpu != self._cpu:
            self._cpu = cpu
            cpu_color = Colors.DANGER if cpu > 50 else Colors.WARNING if cpu > 20 else Colors.TEXT_SECONDARY
            self._cpu_label.configure(text=f"{cpu:.1f}%", text_color=cpu_color)

        # Memory
        mem = proc_data.get("memory_mb", 0.0)
        if mem != self._mem:
            self._mem = mem
            mem_text = f"{mem:.0f} MB" if mem < 1024 else f"{mem / 1024:.1f} GB"
            mem_color = Colors.DANGER if mem > 500 else Colors.WARNING if mem > 200 else Colors.TEXT_SECONDARY
            self._mem_label.configure(text=mem_text, text_color=mem_color)


class ProcessSection(ctk.CTkFrame):
    """A collapsible section grouping processes with smart top-consumer pagination,
    aggregate duplicate system processes, and zero-tearing updates."""

    def __init__(self, master, section_key, title, subtitle, icon, accent_color,
                 default_expanded=True, default_limit=15, on_kill=None, on_inspect=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._key = section_key
        self._title = title
        self._subtitle = subtitle
        self._icon = icon
        self._accent = accent_color
        self._expanded = default_expanded
        self._limit = default_limit
        self._show_all = False
        self._on_kill = on_kill
        self._on_inspect = on_inspect

        self._row_widgets = {}          # pid -> ProcessRow
        self._current_order_pids = []
        self._all_procs_cache = []
        self._empty_label = None

        # Section Header Card
        self._header_card = ctk.CTkFrame(
            self,
            fg_color=Colors.BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER,
            cursor="hand2",
        )
        self._header_card.pack(fill="x", pady=(0, 4))

        h_inner = ctk.CTkFrame(self._header_card, fg_color="transparent", cursor="hand2")
        h_inner.pack(fill="x", padx=16, pady=10)

        # Left: Icon & Title
        left = ctk.CTkFrame(h_inner, fg_color="transparent", cursor="hand2")
        left.pack(side="left", fill="x", expand=True)

        title_row = ctk.CTkFrame(left, fg_color="transparent", cursor="hand2")
        title_row.pack(anchor="w")

        ctk.CTkLabel(
            title_row,
            text=icon,
            font=Fonts.ICON,
            cursor="hand2",
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            title_row,
            text=title,
            font=Fonts.HEADING_3,
            text_color=Colors.TEXT_PRIMARY,
            cursor="hand2",
        ).pack(side="left")

        self._badge_label = ctk.CTkLabel(
            title_row,
            text="",
            font=Fonts.CAPTION,
            text_color=Colors.TEXT_TERTIARY,
            cursor="hand2",
        )
        self._badge_label.pack(side="left", padx=(10, 0))

        ctk.CTkLabel(
            left,
            text=subtitle,
            font=Fonts.TINY,
            text_color=Colors.TEXT_TERTIARY,
            cursor="hand2",
        ).pack(anchor="w", pady=(1, 0))

        # Right: Toggle button
        self._toggle_btn = ctk.CTkButton(
            h_inner,
            text="▾" if default_expanded else "▸",
            font=Fonts.BODY_BOLD,
            fg_color="transparent",
            hover_color=Colors.BG_CARD_HOVER,
            text_color=Colors.TEXT_SECONDARY,
            width=28,
            height=28,
            corner_radius=4,
            command=self._toggle_expand,
        )
        self._toggle_btn.pack(side="right")

        for w in (self._header_card, h_inner, left, title_row, self._badge_label):
            w.bind("<Button-1>", lambda e: self._toggle_expand())

        # Rows Container
        self._container = ctk.CTkFrame(self, fg_color="transparent")
        if default_expanded:
            self._container.pack(fill="x", padx=(6, 0), pady=(0, 8))

        # Column Header with uniform column widths matching rows
        self._col_header = ctk.CTkFrame(
            self._container,
            fg_color=Colors.BG_SECONDARY,
            corner_radius=6,
        )
        self._col_header.pack(fill="x", pady=(0, 3))

        configure_process_columns(self._col_header)

        cols = [
            ("Application / Process", 0, "w", (16, 8)),
            ("PID", 1, "w", (10, 8)),
            ("⚡ Battery Drain", 2, "w", (10, 8)),
            ("CPU", 3, "w", (10, 8)),
            ("Memory", 4, "w", (10, 8)),
            ("Actions", 5, "e", (0, 16)),
        ]
        for text, col, anchor, pad in cols:
            ctk.CTkLabel(
                self._col_header,
                text=text,
                font=Fonts.TINY,
                text_color=Colors.TEXT_TERTIARY,
                anchor=anchor,
            ).grid(row=0, column=col, sticky="ew", padx=pad, pady=5)

        # Rows frame
        self._rows_frame = ctk.CTkFrame(self._container, fg_color="transparent")
        self._rows_frame.pack(fill="x")

        # Expander footer button (e.g. "Show all 98 processes")
        self._expander_frame = ctk.CTkFrame(self._container, fg_color="transparent")
        self._expander_btn = ctk.CTkButton(
            self._expander_frame,
            text="",
            font=Fonts.CAPTION_BOLD,
            fg_color=Colors.BG_CARD,
            hover_color=Colors.BG_CARD_HOVER,
            text_color=Colors.ACCENT,
            border_width=1,
            border_color=Colors.BORDER,
            height=28,
            corner_radius=6,
            command=self._toggle_show_all,
        )
        self._expander_btn.pack(fill="x", pady=(3, 0))

    def _toggle_expand(self):
        """Toggle section expand/collapse."""
        self._expanded = not self._expanded
        if self._expanded:
            self._toggle_btn.configure(text="▾")
            self._container.pack(fill="x", padx=(6, 0), pady=(0, 8))
        else:
            self._toggle_btn.configure(text="▸")
            self._container.pack_forget()

    def _toggle_show_all(self):
        """Toggle showing top consumers vs all processes."""
        self._show_all = not self._show_all
        self._render_rows(force_reorder=True)

    def update_processes(self, procs, is_hovering=False, force_reorder=False):
        """Update section processes with duplicate aggregation and smart limit."""
        if self._key == "system":
            self._all_procs_cache = aggregate_processes(procs, is_dict=True)
        else:
            self._all_procs_cache = procs

        # Update header badge
        count = len(procs)
        total_pwr = round(sum(p["power_percent"] for p in procs), 1)
        total_mem = round(sum(p["memory_mb"] for p in procs), 1)
        mem_str = f"{total_mem:.0f} MB" if total_mem < 1024 else f"{total_mem / 1024:.1f} GB"
        badge_text = f"•  {count} item{'s' if count != 1 else ''}  •  ⚡ {total_pwr:.1f}% Drain  •  {mem_str}"
        self._badge_label.configure(text=badge_text)

        self._render_rows(is_hovering=is_hovering, force_reorder=force_reorder)

    def _render_rows(self, is_hovering=False, force_reorder=False):
        """Render or update visible rows with zero tearing."""
        total_items = len(self._all_procs_cache)

        # Determine visible slice
        if self._limit and not self._show_all and total_items > self._limit:
            visible_procs = self._all_procs_cache[:self._limit]
            has_more = True
            remaining = total_items - self._limit
        else:
            visible_procs = self._all_procs_cache
            has_more = False
            remaining = 0

        target_pids = [p["pid"] for p in visible_procs]
        target_pids_set = set(target_pids)

        # 1. Empty state
        if not target_pids:
            for pid, row in list(self._row_widgets.items()):
                row.destroy()
            self._row_widgets.clear()
            self._current_order_pids.clear()
            self._expander_frame.pack_forget()

            if not self._empty_label:
                self._empty_label = ctk.CTkLabel(
                    self._rows_frame,
                    text=f"No {self._title.lower()} currently running",
                    font=Fonts.CAPTION,
                    text_color=Colors.TEXT_TERTIARY,
                )
                self._empty_label.pack(pady=10)
            return
        else:
            if self._empty_label:
                self._empty_label.destroy()
                self._empty_label = None

        # 2. Destroy row widgets no longer visible
        for pid in list(self._row_widgets.keys()):
            if pid not in target_pids_set:
                self._row_widgets[pid].destroy()
                del self._row_widgets[pid]

        # 3. Create or update row widgets in-place
        newly_created = False
        for p in visible_procs:
            pid = p["pid"]
            if pid in self._row_widgets:
                self._row_widgets[pid].update_data(p)
            else:
                row = ProcessRow(
                    self._rows_frame,
                    p,
                    on_kill=self._on_kill,
                    on_inspect=self._on_inspect,
                )
                self._row_widgets[pid] = row
                newly_created = True

        # 4. Repack only when required (force_reorder, newly created, or initially empty).
        # On periodic updates, in-place updates keep the UI silky-smooth without jumping or geometry renegotiation.
        needs_repack = force_reorder or newly_created or (not self._current_order_pids)
        if needs_repack:
            for pid in target_pids:
                row = self._row_widgets.get(pid)
                if row:
                    row.pack(fill="x", pady=2)
            self._current_order_pids = list(target_pids)

        # 5. Expander button management
        if has_more:
            self._expander_btn.configure(text=f"▾ Show remaining {remaining} {self._title.lower()} (or filter with search)")
            self._expander_frame.pack(fill="x")
        elif self._limit and total_items > self._limit and self._show_all:
            self._expander_btn.configure(text=f"▴ Show top {self._limit} consumers only")
            self._expander_frame.pack(fill="x")
        else:
            self._expander_frame.pack_forget()


class ProcessesView(ctk.CTkFrame):
    """Process tracker view divided into 3 distinct sections with live battery drain %,
    top consumer banner, zero-tearing layout, and Clean Sweep cleanup."""

    def __init__(self, master, process_tracker, **kwargs):
        super().__init__(master, fg_color=Colors.BG_PRIMARY, **kwargs)

        self._tracker = process_tracker
        self._update_job = None
        self._search_debounce_job = None

        self._search_var = ctk.StringVar()
        self._sort_by = "power_percent"
        self._sort_reverse = True
        self._active_filter = "all"      # "all", "active_apps", "background", "system"

        # Refresh management
        self._refresh_rate_sec = 5
        self._is_paused = False
        self._is_mouse_over_list = False
        self._active_inspect_dialog = None
        self._sweep_dialog = None

        self._sections = {}              # key -> ProcessSection
        self._filter_buttons = {}        # key -> CTkButton

        self._build_ui()
        self._start_updates()

    def _build_ui(self):
        """Build the sectioned process list UI."""
        # Scrollable Outer Container
        self._scroll_container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=Colors.BG_ELEVATED,
            scrollbar_button_hover_color=Colors.BORDER_LIGHT,
        )
        self._scroll_container.pack(fill="both", expand=True, padx=20, pady=(12, 10))

        self._scroll_container.bind("<Enter>", lambda e: setattr(self, "_is_mouse_over_list", True))
        self._scroll_container.bind("<Leave>", lambda e: setattr(self, "_is_mouse_over_list", False))

        # Header Title Area
        header = ctk.CTkFrame(self._scroll_container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="Processes & Battery Drain",
            font=Fonts.HEADING_1,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="Monitor relative power consumption across active applications, background utilities, and system services",
            font=Fonts.CAPTION,
            text_color=Colors.TEXT_TERTIARY,
        ).pack(anchor="w", pady=(1, 0))

        right_box = ctk.CTkFrame(header, fg_color="transparent")
        right_box.pack(side="right")

        self._live_indicator = ctk.CTkLabel(
            right_box,
            text="● Live Updates",
            font=Fonts.CAPTION_BOLD,
            text_color=Colors.SUCCESS,
            fg_color=Colors.SUCCESS_BG,
            corner_radius=5,
            padx=8,
            pady=2,
        )
        self._live_indicator.pack(side="right", padx=(8, 0))

        self._count_label = ctk.CTkLabel(
            right_box,
            text="0 processes",
            font=Fonts.CAPTION,
            text_color=Colors.TEXT_SECONDARY,
        )
        self._count_label.pack(side="right")

        # Top Battery Drain Breakdown Card
        self._breakdown_card = ctk.CTkFrame(
            self._scroll_container,
            fg_color=Colors.BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER,
        )
        self._breakdown_card.pack(fill="x", pady=(0, 10))

        bc_inner = ctk.CTkFrame(self._breakdown_card, fg_color="transparent")
        bc_inner.pack(fill="x", padx=16, pady=12)

        # Top consumer banner
        self._top_consumer_label = ctk.CTkLabel(
            bc_inner,
            text="⚡ Analyzing active battery power drain...",
            font=Fonts.HEADING_3,
            text_color=Colors.WARNING,
            anchor="w",
        )
        self._top_consumer_label.pack(fill="x", pady=(0, 8))

        # 3-column section stats bar
        stats_grid = ctk.CTkFrame(bc_inner, fg_color="transparent")
        stats_grid.pack(fill="x")
        stats_grid.grid_columnconfigure((0, 1, 2), weight=1)

        self._chip_active = self._create_stat_chip(stats_grid, 0, "🟢 Active Apps", "0 apps • 0.0% drain", Colors.SUCCESS)
        self._chip_bg = self._create_stat_chip(stats_grid, 1, "📦 Background", "0 procs • 0.0% drain", Colors.PURPLE)
        self._chip_sys = self._create_stat_chip(stats_grid, 2, "🛡️ System", "0 services • 0.0% drain", Colors.ACCENT)

        # Controls & Filter Bar
        controls = ctk.CTkFrame(self._scroll_container, fg_color="transparent")
        controls.pack(fill="x", pady=(0, 10))

        # Filter Pills (All / Active / Background / System)
        filter_box = ctk.CTkFrame(controls, fg_color="transparent")
        filter_box.pack(side="left")

        filters = [
            ("all", "All"),
            ("active_apps", "🟢 Active"),
            ("background", "📦 Background"),
            ("system", "🛡️ System"),
        ]
        for f_key, f_label in filters:
            btn = ctk.CTkButton(
                filter_box,
                text=f_label,
                font=Fonts.CAPTION_BOLD,
                fg_color=Colors.BG_ELEVATED if f_key == "all" else "transparent",
                hover_color=Colors.BG_CARD_HOVER,
                text_color=Colors.TEXT_PRIMARY if f_key == "all" else Colors.TEXT_SECONDARY,
                border_width=1,
                border_color=Colors.BORDER,
                height=32,
                corner_radius=6,
                command=lambda k=f_key: self._set_filter(k),
            )
            btn.pack(side="left", padx=(0, 4))
            self._filter_buttons[f_key] = btn

        # Clean Sweep button
        self._sweep_btn = ctk.CTkButton(
            controls,
            text="⚡ Clean Sweep",
            font=Fonts.CAPTION_BOLD,
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            height=32,
            corner_radius=6,
            command=self._on_clean_sweep,
        )
        self._sweep_btn.pack(side="right")

        # Refresh button
        self._refresh_btn = ctk.CTkButton(
            controls,
            text="↻ Refresh",
            font=Fonts.CAPTION,
            fg_color=Colors.BG_CARD,
            hover_color=Colors.BG_CARD_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            border_width=1,
            border_color=Colors.BORDER,
            height=32,
            width=75,
            corner_radius=6,
            command=lambda: self._refresh_list(force_reorder=True),
        )
        self._refresh_btn.pack(side="right", padx=(0, 6))

        # Refresh rate dropdown (includes '⏸ Paused' option)
        self._rate_menu = ctk.CTkOptionMenu(
            controls,
            values=["⚡ 5s", "⚡ 10s", "⚡ 2s", "⏸ Paused"],
            font=Fonts.CAPTION,
            fg_color=Colors.BG_CARD,
            button_color=Colors.BG_ELEVATED,
            button_hover_color=Colors.BORDER_LIGHT,
            dropdown_fg_color=Colors.BG_ELEVATED,
            dropdown_hover_color=Colors.BG_CARD_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            height=32,
            width=85,
            corner_radius=6,
            command=self._on_rate_change,
        )
        self._rate_menu.set("⚡ 5s")
        self._rate_menu.pack(side="right", padx=(0, 6))

        # Sort menu
        self._sort_menu = ctk.CTkOptionMenu(
            controls,
            values=[
                "⚡ Battery Drain ↓",
                "Memory ↓",
                "Memory ↑",
                "CPU ↓",
                "CPU ↑",
                "Name A-Z",
            ],
            font=Fonts.CAPTION,
            fg_color=Colors.BG_CARD,
            button_color=Colors.BG_ELEVATED,
            button_hover_color=Colors.BORDER_LIGHT,
            dropdown_fg_color=Colors.BG_ELEVATED,
            dropdown_hover_color=Colors.BG_CARD_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            height=32,
            width=135,
            corner_radius=6,
            command=self._on_sort_change,
        )
        self._sort_menu.set("⚡ Battery Drain ↓")
        self._sort_menu.pack(side="right", padx=(0, 6))

        # Search Bar row
        search_row = ctk.CTkFrame(self._scroll_container, fg_color="transparent")
        search_row.pack(fill="x", pady=(0, 10))

        self._search_entry = ctk.CTkEntry(
            search_row,
            textvariable=self._search_var,
            placeholder_text="Search processes by application name, window title, or PID...",
            font=Fonts.BODY_SMALL,
            fg_color=Colors.BG_CARD,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY,
            placeholder_text_color=Colors.TEXT_TERTIARY,
            height=34,
            corner_radius=6,
        )
        self._search_entry.pack(fill="x")
        self._search_var.trace_add("write", self._on_search_typed)

        # 3 Process Sections
        sections_config = [
            (
                "active_apps",
                "Active Applications",
                "User-opened applications currently running with visible interactive windows",
                "🟢",
                Colors.SUCCESS,
                True,   # Expanded
                None,   # No limit: active apps are few
            ),
            (
                "background",
                "Background Processes",
                "Background helpers, closed-to-tray utilities, and non-interactive applications",
                "📦",
                Colors.PURPLE,
                True,   # Expanded
                15,     # Show top 15 by default to prevent coordinate overflow
            ),
            (
                "system",
                "System Processes",
                "Windows core operating system services, drivers, and background daemons (Protected)",
                "🛡️",
                Colors.ACCENT,
                False,  # Collapsed by default
                20,
            ),
        ]

        for key, title, subtitle, icon, accent, expanded, limit in sections_config:
            sec = ProcessSection(
                self._scroll_container,
                section_key=key,
                title=title,
                subtitle=subtitle,
                icon=icon,
                accent_color=accent,
                default_expanded=expanded,
                default_limit=limit,
                on_kill=self._kill_process,
                on_inspect=self._inspect_process,
            )
            sec.pack(fill="x", pady=(0, 8))
            self._sections[key] = sec

        # Status notification bar
        self._status_label = ctk.CTkLabel(
            self,
            text="",
            font=Fonts.CAPTION,
            text_color=Colors.SUCCESS,
        )
        self._status_label.pack(fill="x", padx=20, pady=(0, 4))

    def _create_stat_chip(self, parent, col, title, initial_value, color):
        card = ctk.CTkFrame(
            parent,
            fg_color=Colors.BG_SECONDARY,
            corner_radius=6,
            border_width=1,
            border_color=Colors.BORDER,
        )
        card.grid(
            row=0, column=col, sticky="nsew",
            padx=(0 if col == 0 else 4, 4 if col < 2 else 0),
        )

        ctk.CTkLabel(
            card,
            text=title,
            font=Fonts.TINY,
            text_color=color,
        ).pack(anchor="w", padx=12, pady=(8, 0))

        val_lbl = ctk.CTkLabel(
            card,
            text=initial_value,
            font=Fonts.CAPTION_BOLD,
            text_color=Colors.TEXT_PRIMARY,
        )
        val_lbl.pack(anchor="w", padx=12, pady=(1, 8))

        return val_lbl

    def _set_filter(self, filter_key):
        """Set active section filter pill."""
        self._active_filter = filter_key
        for k, btn in self._filter_buttons.items():
            if k == filter_key:
                btn.configure(fg_color=Colors.BG_ELEVATED, text_color=Colors.TEXT_PRIMARY)
            else:
                btn.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)

        # Show/hide sections accordingly
        for sec_key, sec_widget in self._sections.items():
            if filter_key == "all" or filter_key == sec_key:
                sec_widget.pack(fill="x", pady=(0, 8))
            else:
                sec_widget.pack_forget()

        self._refresh_list(force_reorder=True)

    def _on_search_typed(self, *args):
        """Debounce search input by 150ms."""
        if self._search_debounce_job:
            self.after_cancel(self._search_debounce_job)
        self._search_debounce_job = self.after(150, lambda: self._refresh_list(force_reorder=True))

    def _on_sort_change(self, choice):
        """Handle sort menu change."""
        sort_map = {
            "⚡ Battery Drain ↓": ("power_percent", True),
            "Memory ↓": ("memory_mb", True),
            "Memory ↑": ("memory_mb", False),
            "CPU ↓": ("cpu_percent", True),
            "CPU ↑": ("cpu_percent", False),
            "Name A-Z": ("name", False),
        }
        self._sort_by, self._sort_reverse = sort_map.get(choice, ("power_percent", True))
        self._refresh_list(force_reorder=True)

    def _on_rate_change(self, choice):
        """Handle refresh interval change."""
        if "Paused" in choice:
            self._set_paused(True)
        else:
            self._set_paused(False)
            if "2s" in choice:
                self._refresh_rate_sec = 2
            elif "10s" in choice:
                self._refresh_rate_sec = 10
            else:
                self._refresh_rate_sec = 5
            self._schedule_update()

    def _set_paused(self, paused):
        """Set pause state and update indicators."""
        self._is_paused = paused
        if paused:
            self._live_indicator.configure(
                text="⏸ Paused",
                text_color=Colors.WARNING,
                fg_color=Colors.WARNING_BG,
            )
            self._rate_menu.set("⏸ Paused")
            if self._update_job:
                self.after_cancel(self._update_job)
        else:
            self._live_indicator.configure(
                text="● Live Updates",
                text_color=Colors.SUCCESS,
                fg_color=Colors.SUCCESS_BG,
            )
            self._rate_menu.set(f"⚡ {self._refresh_rate_sec}s")
            self._schedule_update()

    def _start_updates(self):
        """Start periodic UI refresh."""
        self._refresh_list(force_reorder=True)
        self._schedule_update()

    def _schedule_update(self):
        if self._update_job:
            self.after_cancel(self._update_job)
        if not self._is_paused:
            self._update_job = self.after(self._refresh_rate_sec * 1000, self._periodic_update)

    def _periodic_update(self):
        """Timer callback for regular refreshes."""
        self._refresh_list()
        self._schedule_update()

    def _refresh_list(self, force_reorder=False):
        """Refresh process sections from tracker data."""
        sections_data = self._tracker.get_processes_by_section()
        stats = self._tracker.get_section_stats()
        search = self._search_var.get().strip().lower()

        # Update Top Consumer highlight
        top = stats.get("top_consumer")
        if top and top.get("power_percent", 0.0) > 0.0:
            pname = top.get("window_title") or top.get("name") or "Unknown"
            if len(pname) > 40:
                pname = pname[:37] + "..."
            sec_display = top.get("section", "active_apps").replace("_", " ").title()
            self._top_consumer_label.configure(
                text=f"⚡ {pname} is the top battery consumer ({top['power_percent']:.1f}% relative drain in {sec_display})",
                text_color=Colors.WARNING if top["power_percent"] > 10 else Colors.ACCENT,
            )
        else:
            self._top_consumer_label.configure(
                text="⚡ Relative Battery Power Drain is balanced across running tasks",
                text_color=Colors.TEXT_SECONDARY,
            )

        # Update Section Stat Chips
        act_s = stats.get("active_apps", {})
        bg_s = stats.get("background", {})
        sys_s = stats.get("system", {})

        self._chip_active.configure(
            text=f"{act_s.get('count', 0)} apps • {act_s.get('power_percent', 0.0):.1f}% drain"
        )
        self._chip_bg.configure(
            text=f"{bg_s.get('count', 0)} procs • {bg_s.get('power_percent', 0.0):.1f}% drain"
        )
        self._chip_sys.configure(
            text=f"{sys_s.get('count', 0)} services • {sys_s.get('power_percent', 0.0):.1f}% drain"
        )

        # Process counts
        total_p = self._tracker.get_total_count()
        user_p = self._tracker.get_process_count()
        self._count_label.configure(text=f"{user_p} user apps  ({total_p} total)")

        # Filter & Sort each section
        for sec_key, sec_widget in self._sections.items():
            procs = sections_data.get(sec_key, [])

            if search:
                procs = [
                    p for p in procs
                    if search in p["name"].lower()
                    or search in (p.get("window_title") or "").lower()
                    or search in str(p["pid"])
                ]

            try:
                procs.sort(key=lambda p: p.get(self._sort_by, 0), reverse=self._sort_reverse)
            except TypeError:
                procs.sort(key=lambda p: str(p.get(self._sort_by, "")), reverse=self._sort_reverse)

            sec_widget.update_processes(
                procs,
                is_hovering=self._is_mouse_over_list,
                force_reorder=force_reorder,
            )

    def _inspect_process(self, pid):
        """Open detailed process inspection dialog."""
        details = self._tracker.get_process_details(pid)
        if not details:
            return

        if self._active_inspect_dialog is not None:
            try:
                if self._active_inspect_dialog.winfo_exists():
                    self._active_inspect_dialog.destroy()
            except Exception:
                pass

        self._active_inspect_dialog = ProcessDetailsDialog(
            self,
            proc_details=details,
            on_kill=self._kill_process,
        )

    def _kill_process(self, pid):
        """Kill a single process asynchronously with immediate UI feedback."""
        def worker():
            success = self._tracker.kill_process(pid)
            self.after(0, lambda: self._on_kill_completed(pid, success))

        threading.Thread(target=worker, daemon=True).start()

    def _on_kill_completed(self, pid, success):
        """Handle kill completion on the GUI thread."""
        if success:
            self._status_label.configure(
                text=f"✓ Process {pid} terminated successfully",
                text_color=Colors.SUCCESS,
            )
        else:
            self._status_label.configure(
                text=f"✕ Failed to terminate process {pid} (Protected or Access Denied)",
                text_color=Colors.DANGER,
            )
        self.after(3000, lambda: self._status_label.configure(text=""))
        self._refresh_list(force_reorder=True)

    def _on_clean_sweep(self):
        """Execute clean sweep with confirmation and non-blocking background execution."""
        count = self._tracker.get_process_count()
        if count == 0:
            self._status_label.configure(
                text="ℹ No user applications to clean",
                text_color=Colors.TEXT_SECONDARY,
            )
            return

        def run_sweep():
            self._status_label.configure(
                text="⚡ Clean Sweep in progress...",
                text_color=Colors.WARNING,
            )

            def worker():
                terminated = self._tracker.clean_sweep()
                self.after(0, lambda: self._on_sweep_completed(terminated))

            threading.Thread(target=worker, daemon=True).start()

        msg = (
            f"Are you sure you want to close {count} user application(s)?\n\n"
            "• All unsaved work in user apps may be lost.\n"
            "• System-critical services and PowerPilot are strictly protected."
        )
        ConfirmActionDialog(
            master=self,
            title="Clean Sweep — Close User Applications",
            heading="⚡ Clean Sweep Confirmation",
            message=msg,
            confirm_text="Yes, Close Applications",
            on_confirm=run_sweep,
        )

    def _on_sweep_completed(self, count):
        """Handle Clean Sweep completion."""
        self._status_label.configure(
            text=f"✓ Clean Sweep complete — {count} application(s) terminated",
            text_color=Colors.SUCCESS,
        )
        self.after(4000, lambda: self._status_label.configure(text=""))
        self._refresh_list(force_reorder=True)

    def on_show(self):
        """Lifecycle hook: page became visible."""
        self._refresh_list(force_reorder=True)
        if not self._is_paused:
            self._schedule_update()

    def on_hide(self):
        """Lifecycle hook: page navigated away."""
        if self._update_job:
            self.after_cancel(self._update_job)
            self._update_job = None
        if self._search_debounce_job:
            self.after_cancel(self._search_debounce_job)
            self._search_debounce_job = None
