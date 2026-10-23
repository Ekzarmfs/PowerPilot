"""
Battery Optimizer view for PowerPilot.
Provides categorized process management to disable non-essential Windows/Microsoft
and third-party background processes for longer battery life.
"""

import customtkinter as ctk
import threading
import psutil

from ui.theme import Colors, Fonts, Dimensions
from ui.processes import ProcessDetailsDialog, ConfirmActionDialog, aggregate_processes


# ── Category metadata ──────────────────────────────────────────────
CATEGORY_META = {
    "windows": {
        "icon": "🪟",
        "label": "Windows & System",
        "description": "Built-in Windows background services and UX components",
        "accent": Colors.ACCENT,
    },
    "microsoft": {
        "icon": "Ⓜ️",
        "label": "Microsoft Apps",
        "description": "Microsoft Office, Teams, OneDrive, and other Microsoft software",
        "accent": Colors.WARNING,
    },
    "third_party": {
        "icon": "📦",
        "label": "Third-Party Apps",
        "description": "All other applications installed on your system",
        "accent": Colors.PURPLE,
    },
}

CATEGORY_ORDER = ["windows", "microsoft", "third_party"]


class OptimizerProcessRow(ctk.CTkFrame):
    """A single process row inside a category section with double-click inspection."""

    def __init__(self, master, proc, on_toggle, on_inspect=None, **kwargs):
        super().__init__(
            master,
            fg_color=Colors.BG_CARD,
            corner_radius=6,
            cursor="hand2",
            **kwargs,
        )

        self._proc = proc
        self._on_toggle = on_toggle
        self._on_inspect = on_inspect

        inner = ctk.CTkFrame(self, fg_color="transparent", cursor="hand2")
        inner.pack(fill="both", expand=True, padx=10, pady=5)
        inner.grid_columnconfigure(0, weight=3)   # Name
        inner.grid_columnconfigure(1, weight=2)   # Description
        inner.grid_columnconfigure(2, weight=1)   # Memory
        inner.grid_columnconfigure(3, weight=1)   # CPU
        inner.grid_columnconfigure(4, weight=0)   # Toggle/Kill

        # Process name
        name_color = Colors.TEXT_TERTIARY if proc.is_mandatory else Colors.TEXT_PRIMARY
        name_lbl = ctk.CTkLabel(
            inner,
            text=proc.name,
            font=Fonts.BODY,
            text_color=name_color,
            anchor="w",
            cursor="hand2",
        )
        name_lbl.grid(row=0, column=0, sticky="w")

        # Description
        desc = proc.description or proc.category.replace("_", " ").title()
        desc_lbl = ctk.CTkLabel(
            inner,
            text=desc,
            font=Fonts.TINY,
            text_color=Colors.TEXT_TERTIARY,
            anchor="w",
            cursor="hand2",
        )
        desc_lbl.grid(row=0, column=1, sticky="w", padx=(4, 0))

        # Memory
        mem = proc.memory_mb
        mem_text = f"{mem:.1f} MB" if mem < 1024 else f"{mem / 1024:.1f} GB"
        mem_color = Colors.DANGER if mem > 300 else Colors.WARNING if mem > 100 else Colors.TEXT_SECONDARY
        mem_lbl = ctk.CTkLabel(
            inner,
            text=mem_text,
            font=Fonts.BODY_SMALL,
            text_color=mem_color,
            anchor="center",
            cursor="hand2",
        )
        mem_lbl.grid(row=0, column=2, sticky="ew")

        # CPU
        cpu = proc.cpu_percent
        cpu_color = Colors.DANGER if cpu > 50 else Colors.WARNING if cpu > 20 else Colors.TEXT_SECONDARY
        cpu_lbl = ctk.CTkLabel(
            inner,
            text=f"{cpu:.1f}%",
            font=Fonts.BODY_SMALL,
            text_color=cpu_color,
            anchor="center",
            cursor="hand2",
        )
        cpu_lbl.grid(row=0, column=3, sticky="ew")

        # Toggle button or mandatory label
        if proc.is_mandatory:
            ctk.CTkLabel(
                inner,
                text="Protected",
                font=Fonts.TINY,
                text_color=Colors.TEXT_TERTIARY,
                anchor="center",
            ).grid(row=0, column=4, sticky="e", padx=(6, 0))
        else:
            kill_btn = ctk.CTkButton(
                inner,
                text="Stop",
                font=Fonts.TINY,
                fg_color="transparent",
                hover_color=Colors.DANGER_BG,
                text_color=Colors.DANGER,
                width=42,
                height=22,
                corner_radius=4,
                border_width=1,
                border_color=Colors.BORDER,
                command=lambda: self._on_toggle(proc.pid),
            )
            kill_btn.grid(row=0, column=4, sticky="e", padx=(6, 0))

        self._is_hovered = False

        # Double-click and hover bindings
        def handle_dbl_click(event=None):
            if self._on_inspect:
                self._on_inspect(self._proc.pid)

        self.bind("<Double-Button-1>", handle_dbl_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        for w in (inner, name_lbl, desc_lbl, mem_lbl, cpu_lbl):
            w.bind("<Double-Button-1>", handle_dbl_click)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

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
                return
        except Exception:
            pass
        if self._is_hovered:
            self._is_hovered = False
            self.configure(fg_color=Colors.BG_CARD)


class CategorySection(ctk.CTkFrame):
    """A collapsible category section with process rows."""

    def __init__(self, master, category_key, processes, on_kill_process,
                 on_kill_category, on_inspect=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        meta = CATEGORY_META.get(category_key, {})
        self._meta = meta
        self._category = category_key
        self._processes = processes
        self._on_kill_process = on_kill_process
        self._on_kill_category = on_kill_category
        self._on_inspect = on_inspect
        self._expanded = True
        self._show_all = False
        self._limit = 15 if category_key == "windows" else 25
        self._rows_frame = None

        # ── Category header ─────────────────────────────────────────
        header_card = ctk.CTkFrame(
            self,
            fg_color=Colors.BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER,
        )
        header_card.pack(fill="x", pady=(0, 2))

        header_inner = ctk.CTkFrame(header_card, fg_color="transparent")
        header_inner.pack(fill="x", padx=16, pady=10)

        # Left: icon + label
        left = ctk.CTkFrame(header_inner, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        title_row = ctk.CTkFrame(left, fg_color="transparent")
        title_row.pack(fill="x")

        ctk.CTkLabel(
            title_row,
            text=meta.get("icon", "📁"),
            font=("Segoe UI Emoji", 14),
        ).pack(side="left")

        ctk.CTkLabel(
            title_row,
            text=f"  {meta.get('label', category_key)}",
            font=Fonts.HEADING_3,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        # Count badge
        killable = len([p for p in processes if not p.is_mandatory])
        total = len(processes)
        total_mem = round(sum(p.memory_mb for p in processes), 1)
        mem_str = f"{total_mem:.0f} MB" if total_mem < 1024 else f"{total_mem / 1024:.1f} GB"

        ctk.CTkLabel(
            title_row,
            text=f"  {total} process{'es' if total != 1 else ''}  ·  {mem_str}",
            font=Fonts.CAPTION,
            text_color=Colors.TEXT_TERTIARY,
        ).pack(side="left", padx=(6, 0))

        ctk.CTkLabel(
            left,
            text=meta.get("description", ""),
            font=Fonts.TINY,
            text_color=Colors.TEXT_TERTIARY,
        ).pack(anchor="w", pady=(1, 0))

        # Right: Kill category button
        if killable > 0:
            cat_btn = ctk.CTkButton(
                header_inner,
                text=f"Stop All ({killable})",
                font=Fonts.BODY_BOLD,
                fg_color=Colors.DANGER_BG,
                hover_color=Colors.DANGER,
                text_color=Colors.DANGER,
                width=110,
                height=30,
                corner_radius=6,
                border_width=1,
                border_color=Colors.DANGER,
                command=lambda: self._on_kill_category(self._category),
            )
            cat_btn.pack(side="right", padx=(6, 0))

        # Expand/Collapse toggle
        self._toggle_btn = ctk.CTkButton(
            header_inner,
            text="▼",
            font=Fonts.BODY,
            fg_color="transparent",
            hover_color=Colors.BG_CARD_HOVER,
            text_color=Colors.TEXT_TERTIARY,
            width=28,
            height=28,
            corner_radius=4,
            command=self._toggle_expand,
        )
        self._toggle_btn.pack(side="right")

        # Make header clickable to toggle
        for w in (left, title_row):
            w.configure(cursor="hand2")
            w.bind("<Button-1>", self._toggle_expand)

        # ── Process rows ────────────────────────────────────────────
        self._rows_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._rows_frame.pack(fill="x", padx=(12, 0), pady=(0, 6))

        self._render_rows()

    def _toggle_expand(self, event=None):
        """Toggle category section expand/collapse with debounce."""
        if getattr(self, "_click_locked", False):
            return
        self._click_locked = True
        self.after(200, lambda: setattr(self, "_click_locked", False))

        self._expanded = not self._expanded
        if self._expanded:
            self._toggle_btn.configure(text="▼")
            self._rows_frame.pack(fill="x", padx=(12, 0), pady=(0, 6))
        else:
            self._toggle_btn.configure(text="▶")
            self._rows_frame.pack_forget()

    def _render_rows(self):
        """Render all process rows in this category."""
        for widget in self._rows_frame.winfo_children():
            widget.destroy()

        if not self._processes:
            ctk.CTkLabel(
                self._rows_frame,
                text="No processes in this category",
                font=Fonts.CAPTION,
                text_color=Colors.TEXT_TERTIARY,
            ).pack(pady=6)
            return

        # Column headers
        col_header = ctk.CTkFrame(
            self._rows_frame,
            fg_color=Colors.BG_SECONDARY,
            corner_radius=4,
        )
        col_header.pack(fill="x", pady=(0, 2))

        ch_inner = ctk.CTkFrame(col_header, fg_color="transparent")
        ch_inner.pack(fill="both", expand=True, padx=10, pady=4)
        ch_inner.grid_columnconfigure(0, weight=3)
        ch_inner.grid_columnconfigure(1, weight=2)
        ch_inner.grid_columnconfigure(2, weight=1)
        ch_inner.grid_columnconfigure(3, weight=1)
        ch_inner.grid_columnconfigure(4, weight=0)

        for text, col, anchor in [
            ("Process", 0, "w"),
            ("Type", 1, "w"),
            ("Memory", 2, "center"),
            ("CPU", 3, "center"),
            ("Action", 4, "e"),
        ]:
            ctk.CTkLabel(
                ch_inner,
                text=text,
                font=Fonts.TINY,
                text_color=Colors.TEXT_TERTIARY,
                anchor=anchor,
            ).grid(row=0, column=col, sticky="ew")

        # Separate actionable processes and aggregate duplicate mandatory system processes
        actionable = [p for p in self._processes if not p.is_mandatory]
        mandatory = [p for p in self._processes if p.is_mandatory]
        display_mandatory = aggregate_processes(mandatory, is_dict=False)

        actionable.sort(key=lambda p: p.memory_mb, reverse=True)
        display_mandatory.sort(key=lambda p: p.memory_mb, reverse=True)
        final_list = actionable + display_mandatory

        total_items = len(final_list)
        if self._limit and not self._show_all and total_items > self._limit:
            visible_list = final_list[:self._limit]
            remaining = total_items - self._limit
        else:
            visible_list = final_list
            remaining = 0

        for proc in visible_list:
            row = OptimizerProcessRow(
                self._rows_frame,
                proc,
                on_toggle=self._on_kill_process,
                on_inspect=self._on_inspect,
            )
            row.pack(fill="x", pady=1)

        # Expander button for large categories (e.g. Windows system services)
        if remaining > 0:
            exp_btn = ctk.CTkButton(
                self._rows_frame,
                text=f"▾ Show remaining {remaining} processes in {self._meta.get('label', self._category)}",
                font=Fonts.CAPTION,
                fg_color="transparent",
                hover_color=Colors.BG_CARD_HOVER,
                text_color=Colors.ACCENT,
                height=28,
                corner_radius=4,
                command=self._toggle_show_all,
            )
            exp_btn.pack(fill="x", pady=(4, 2))
        elif self._limit and total_items > self._limit and self._show_all:
            col_btn = ctk.CTkButton(
                self._rows_frame,
                text=f"▴ Show top {self._limit} processes only",
                font=Fonts.CAPTION,
                fg_color="transparent",
                hover_color=Colors.BG_CARD_HOVER,
                text_color=Colors.TEXT_TERTIARY,
                height=28,
                corner_radius=4,
                command=self._toggle_show_all,
            )
            col_btn.pack(fill="x", pady=(4, 2))

    def _toggle_show_all(self):
        """Toggle showing all processes vs paginated top consumers."""
        self._show_all = not self._show_all
        self._render_rows()


class OptimizerView(ctk.CTkFrame):
    """Battery optimizer view with categorized background process management."""

    def __init__(self, master, bg_process_manager, process_tracker=None, **kwargs):
        super().__init__(master, fg_color=Colors.BG_PRIMARY, **kwargs)

        self._manager = bg_process_manager
        self._tracker = process_tracker
        self._scanning = False

        self._build_ui()

    def _build_ui(self):
        """Build the optimizer view."""
        # Scrollable container
        self._container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=Colors.BG_ELEVATED,
            scrollbar_button_hover_color=Colors.BORDER_LIGHT,
        )
        self._container.pack(fill="both", expand=True, padx=20, pady=(14, 20))

        # ── Header ──────────────────────────────────────────────────
        header = ctk.CTkFrame(self._container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            header,
            text="Battery Optimizer",
            font=Fonts.HEADING_1,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        self._total_label = ctk.CTkLabel(
            header,
            text="",
            font=Fonts.BODY_SMALL,
            text_color=Colors.TEXT_SECONDARY,
        )
        self._total_label.pack(side="right")

        ctk.CTkLabel(
            self._container,
            text="Scan and manage running processes to extend battery life. "
                 "Disable non-essential services with a single click.",
            font=Fonts.BODY_SMALL,
            text_color=Colors.TEXT_SECONDARY,
            wraplength=700,
            justify="left",
            anchor="w",
        ).pack(fill="x", anchor="w", pady=(0, 10))

        # ── Action bar ──────────────────────────────────────────────
        action_bar = ctk.CTkFrame(
            self._container,
            fg_color=Colors.BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER,
        )
        action_bar.pack(fill="x", pady=(0, 12))

        action_inner = ctk.CTkFrame(action_bar, fg_color="transparent")
        action_inner.pack(fill="x", padx=16, pady=10)

        # Scan button
        self._scan_btn = ctk.CTkButton(
            action_inner,
            text="Scan All Processes",
            font=Fonts.BUTTON,
            fg_color=Colors.ACCENT_DARK,
            hover_color=Colors.ACCENT,
            text_color=Colors.TEXT_PRIMARY,
            height=38,
            width=180,
            corner_radius=6,
            command=self._start_scan,
        )
        self._scan_btn.pack(side="left")

        # Kill Windows/MS button
        self._kill_win_btn = ctk.CTkButton(
            action_inner,
            text="Stop Windows Background",
            font=Fonts.BODY_BOLD,
            fg_color=Colors.WARNING_BG,
            hover_color=Colors.WARNING,
            text_color=Colors.WARNING,
            height=38,
            width=200,
            corner_radius=6,
            border_width=1,
            border_color=Colors.WARNING,
            command=self._kill_windows_bg,
            state="disabled",
        )
        self._kill_win_btn.pack(side="left", padx=(8, 0))

        # Kill ALL non-mandatory
        self._kill_all_btn = ctk.CTkButton(
            action_inner,
            text="Stop All Non-Essential",
            font=Fonts.BODY_BOLD,
            fg_color=Colors.DANGER_BG,
            hover_color=Colors.DANGER,
            text_color=Colors.DANGER,
            height=38,
            width=180,
            corner_radius=6,
            border_width=1,
            border_color=Colors.DANGER,
            command=self._kill_all_non_essential,
            state="disabled",
        )
        self._kill_all_btn.pack(side="right")

        # ── Status ──────────────────────────────────────────────────
        self._status_label = ctk.CTkLabel(
            self._container,
            text="Click 'Scan All Processes' to begin analysis",
            font=Fonts.BODY_SMALL,
            text_color=Colors.TEXT_TERTIARY,
        )
        self._status_label.pack(fill="x", pady=(0, 6))

        # ── Savings summary card (hidden until scan) ────────────────
        self._savings_frame = ctk.CTkFrame(self._container, fg_color="transparent")
        # Will be packed after scan

        # ── Category sections container ─────────────────────────────
        self._categories_frame = ctk.CTkFrame(self._container, fg_color="transparent")
        self._categories_frame.pack(fill="both", expand=True)

    def _start_scan(self):
        """Start a background process scan."""
        if self._scanning:
            return

        self._scanning = True
        self._scan_btn.configure(
            text="Scanning...",
            state="disabled",
            fg_color=Colors.BG_ELEVATED,
        )
        self._status_label.configure(
            text="Scanning all running processes...",
            text_color=Colors.ACCENT,
        )

        # Run scan in background thread
        def scan_thread():
            self._manager.scan_all_processes()
            self.after(0, self._on_scan_complete)

        thread = threading.Thread(target=scan_thread, daemon=True)
        thread.start()

    def _on_scan_complete(self):
        """Called when the background scan finishes."""
        self._scanning = False
        self._scan_btn.configure(
            text="Rescan Processes",
            state="normal",
            fg_color=Colors.ACCENT_DARK,
        )

        # Enable action buttons
        self._kill_win_btn.configure(state="normal")
        self._kill_all_btn.configure(state="normal")

        total = self._manager.get_total_count()
        self._total_label.configure(text=f"{total} processes found")

        potential = self._manager.get_potential_savings_mb()
        pot_str = f"{potential:.0f} MB" if potential < 1024 else f"{potential / 1024:.1f} GB"
        self._status_label.configure(
            text=f"Scan complete — {total} processes found, ~{pot_str} potential memory savings",
            text_color=Colors.SUCCESS,
        )

        self._render_savings_summary()
        self._render_categories()

    def _render_savings_summary(self):
        """Render the savings summary cards."""
        # Clear previous
        for w in self._savings_frame.winfo_children():
            w.destroy()
        self._savings_frame.pack_forget()
        self._savings_frame.pack(fill="x", pady=(0, 12),
                                 before=self._categories_frame)

        stats = self._manager.get_category_stats()

        cards_frame = ctk.CTkFrame(self._savings_frame, fg_color="transparent")
        cards_frame.pack(fill="x")
        cards_frame.grid_columnconfigure((0, 1, 2), weight=1)

        for col_idx, cat_key in enumerate(CATEGORY_ORDER):
            meta = CATEGORY_META[cat_key]
            cat_stats = stats.get(cat_key, {"count": 0, "memory_mb": 0, "killable": 0})

            card = ctk.CTkFrame(
                cards_frame,
                fg_color=Colors.BG_CARD,
                corner_radius=8,
                border_width=1,
                border_color=Colors.BORDER,
            )
            card.grid(
                row=0, column=col_idx, sticky="nsew",
                padx=(0 if col_idx == 0 else 3, 3 if col_idx < 2 else 0),
            )

            card_inner = ctk.CTkFrame(card, fg_color="transparent")
            card_inner.pack(fill="x", padx=14, pady=10)

            ctk.CTkLabel(
                card_inner,
                text=f"{meta['icon']}  {meta['label']}",
                font=Fonts.HEADING_3,
                text_color=meta["accent"],
                anchor="w",
            ).pack(anchor="w")

            mem = cat_stats["memory_mb"]
            mem_str = f"{mem:.0f} MB" if mem < 1024 else f"{mem / 1024:.1f} GB"

            ctk.CTkLabel(
                card_inner,
                text=f"{cat_stats['count']} processes  ·  {mem_str}",
                font=Fonts.BODY_SMALL,
                text_color=Colors.TEXT_SECONDARY,
                anchor="w",
            ).pack(anchor="w", pady=(1, 0))

            ctk.CTkLabel(
                card_inner,
                text=f"{cat_stats['killable']} can be stopped",
                font=Fonts.TINY,
                text_color=Colors.SUCCESS if cat_stats["killable"] > 0 else Colors.TEXT_TERTIARY,
                anchor="w",
            ).pack(anchor="w", pady=(1, 0))

    def _render_categories(self):
        """Render all category sections with their processes."""
        for w in self._categories_frame.winfo_children():
            w.destroy()

        for cat_key in CATEGORY_ORDER:
            processes = self._manager.get_processes_by_category(cat_key)
            if not processes:
                continue

            section = CategorySection(
                self._categories_frame,
                category_key=cat_key,
                processes=processes,
                on_kill_process=self._kill_single,
                on_kill_category=self._kill_category,
                on_inspect=self._inspect_process,
            )
            section.pack(fill="x", pady=(0, 8))

    def _inspect_process(self, pid):
        """Open detailed process inspection dialog from Optimizer."""
        details = self._tracker.get_process_details(pid) if self._tracker else None
        if not details:
            try:
                p = psutil.Process(pid)
                details = {
                    "pid": pid,
                    "name": p.name(),
                    "exe": p.exe() if hasattr(p, "exe") else "N/A",
                    "cmdline": " ".join(p.cmdline()) if hasattr(p, "cmdline") else "",
                    "threads": p.num_threads(),
                    "memory_mb": round(p.memory_info().rss / (1024 * 1024), 1),
                    "cpu_percent": p.cpu_percent(interval=None),
                    "status": "running",
                }
            except Exception:
                return

        ProcessDetailsDialog(self, proc_details=details, on_kill=self._kill_single)

    def _kill_single(self, pid):
        """Kill a single process asynchronously and refresh."""
        self._status_label.configure(
            text=f"Terminating process {pid}...",
            text_color=Colors.ACCENT,
        )

        def worker():
            success = self._manager.kill_process(pid)
            self._manager.scan_all_processes()
            self.after(0, lambda: self._on_single_kill_done(pid, success))

        threading.Thread(target=worker, daemon=True).start()

    def _on_single_kill_done(self, pid, success):
        """Handle single kill completion on GUI thread."""
        if success:
            self._status_label.configure(
                text=f"Process {pid} terminated",
                text_color=Colors.SUCCESS,
            )
        else:
            self._status_label.configure(
                text=f"Failed to terminate process {pid} (access denied or mandatory)",
                text_color=Colors.DANGER,
            )
        self.after(4000, lambda: self._status_label.configure(
            text="", text_color=Colors.TEXT_TERTIARY
        ))
        self._render_savings_summary()
        self._render_categories()
        self._total_label.configure(
            text=f"{self._manager.get_total_count()} processes found"
        )

    def _kill_category(self, category):
        """Kill all non-mandatory processes in a category with confirmation."""
        meta = CATEGORY_META.get(category, {})
        label = meta.get("label", category)
        procs = self._manager.get_processes_by_category(category)
        killable = [p for p in procs if not p.is_mandatory]
        count = len(killable)

        if count == 0:
            self._status_label.configure(
                text="No stoppable processes in this category",
                text_color=Colors.TEXT_SECONDARY,
            )
            return

        mem = round(sum(p.memory_mb for p in killable), 1)
        mem_str = f"{mem:.0f} MB" if mem < 1024 else f"{mem / 1024:.1f} GB"

        def confirm():
            self._status_label.configure(
                text=f"Stopping {label} processes...",
                text_color=Colors.WARNING,
            )

            def bg_kill():
                killed = self._manager.kill_all_non_mandatory(category=category)
                self.after(0, lambda: self._on_category_kill_done(killed, label))

            threading.Thread(target=bg_kill, daemon=True).start()

        msg = (
            f"This will free approximately {mem_str} of memory.\n"
            f"Mandatory system processes will NOT be affected.\n"
            f"Some apps may restart automatically."
        )
        ConfirmActionDialog(
            master=self,
            title=f"Stop {label} Processes",
            heading=f"Stop {count} {label} process{'es' if count != 1 else ''}?",
            message=msg,
            confirm_text=f"Stop All ({count})",
            on_confirm=confirm,
            confirm_color=Colors.DANGER,
        )

    def _on_category_kill_done(self, killed, label):
        """Called when category kill finishes."""
        self._status_label.configure(
            text=f"Stopped {killed} {label} process{'es' if killed != 1 else ''}",
            text_color=Colors.SUCCESS,
        )
        self.after(5000, lambda: self._status_label.configure(text=""))
        self._render_savings_summary()
        self._render_categories()
        self._total_label.configure(
            text=f"{self._manager.get_total_count()} processes found"
        )

    def _kill_windows_bg(self):
        """Kill all non-mandatory Windows/Microsoft background processes."""
        self._kill_category("windows")

    def _kill_all_non_essential(self):
        """Kill ALL non-mandatory processes with confirmation."""
        non_mandatory = self._manager.get_non_mandatory_processes()
        count = len(non_mandatory)

        if count == 0:
            self._status_label.configure(
                text="No non-essential processes to stop",
                text_color=Colors.TEXT_SECONDARY,
            )
            return

        total_mem = round(sum(p.memory_mb for p in non_mandatory), 1)
        mem_str = f"{total_mem:.0f} MB" if total_mem < 1024 else f"{total_mem / 1024:.1f} GB"

        def confirm():
            self._status_label.configure(
                text="Stopping all non-essential processes...",
                text_color=Colors.WARNING,
            )

            def bg_all():
                killed = self._manager.kill_all_non_mandatory()
                self.after(0, lambda: self._on_all_kill_done(killed))

            threading.Thread(target=bg_all, daemon=True).start()

        msg = (
            f"This will terminate all non-mandatory processes across\n"
            f"Windows, Microsoft, and third-party categories.\n\n"
            f"Estimated memory freed: ~{mem_str}\n"
            f"Critical system processes are protected."
        )
        ConfirmActionDialog(
            master=self,
            title="Stop All Non-Essential Processes",
            heading=f"Stop ALL {count} non-essential process{'es' if count != 1 else ''}?",
            message=msg,
            confirm_text=f"Stop All ({count})",
            on_confirm=confirm,
            confirm_color=Colors.DANGER,
        )

    def _on_all_kill_done(self, killed):
        """Called when all non-mandatory processes finish stopping."""
        self._status_label.configure(
            text=f"Stopped {killed} non-essential process{'es' if killed != 1 else ''} — battery life extended!",
            text_color=Colors.SUCCESS,
        )
        self.after(6000, lambda: self._status_label.configure(text=""))
        self._render_savings_summary()
        self._render_categories()
        self._total_label.configure(
            text=f"{self._manager.get_total_count()} processes found"
        )
