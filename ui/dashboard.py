"""
Dashboard view for PowerPilot.
Displays a dominant battery gauge as the hero element, inline stat metrics,
power plan status, and Clean Sweep action.
"""

import customtkinter as ctk
import tkinter as tk
import math
import time as time_mod
import threading

from ui.theme import Colors, Fonts, Dimensions, get_battery_color, get_health_color


class BatteryGauge(ctk.CTkFrame):
    """Animated circular battery gauge — the hero telemetry focal point."""

    def __init__(self, master, size=200, **kwargs):
        super().__init__(
            master,
            fg_color="transparent",
            **kwargs,
        )

        self._size = size
        self._percent = 0
        self._target_percent = 0
        self._is_charging = False
        self._status_text = "Detecting..."
        self._animating = False

        # Canvas for drawing the arc gauge
        self._canvas = tk.Canvas(
            self,
            width=size,
            height=size,
            bg=Colors.BG_PRIMARY,
            highlightthickness=0,
        )
        self._canvas.pack()

        self._draw_gauge()

    def _draw_gauge(self):
        """Draw the battery gauge arcs and text."""
        c = self._canvas
        c.delete("all")

        cx = self._size / 2
        cy = self._size / 2
        radius = self._size / 2 - 22
        line_width = 10

        # Background arc (270 degrees, from 135° to -135°)
        self._draw_arc(
            c, cx, cy, radius, 135, -270, Colors.BATTERY_BG, line_width
        )

        # Foreground arc (battery level)
        if self._percent > 0:
            extent = -270 * (self._percent / 100)
            color = get_battery_color(self._percent, self._is_charging)
            self._draw_arc(c, cx, cy, radius, 135, extent, color, line_width)

        # Center percentage text — big, bold hero number
        pct_text = f"{int(self._percent)}%"
        c.create_text(
            cx,
            cy - 10,
            text=pct_text,
            fill=Colors.TEXT_PRIMARY,
            font=Fonts.DISPLAY,
        )

        # Status text below percentage
        c.create_text(
            cx,
            cy + 26,
            text=self._status_text,
            fill=Colors.TEXT_SECONDARY,
            font=Fonts.BODY_SMALL,
        )

        # Charging indicator
        if self._is_charging:
            c.create_text(
                cx,
                cy + 44,
                text="⚡ Charging",
                fill=Colors.ACCENT,
                font=Fonts.CAPTION_BOLD,
            )

    def _draw_arc(self, canvas, cx, cy, radius, start, extent, color, width, stipple=""):
        """Draw an arc on the canvas.

        Args:
            canvas: Tkinter canvas.
            cx, cy: Center coordinates.
            radius: Arc radius.
            start: Start angle in degrees.
            extent: Arc extent in degrees.
            color: Arc color.
            width: Line width.
            stipple: Optional stipple pattern.
        """
        x0 = cx - radius
        y0 = cy - radius
        x1 = cx + radius
        y1 = cy + radius
        canvas.create_arc(
            x0, y0, x1, y1,
            start=start,
            extent=extent,
            outline=color,
            width=width,
            style="arc",
            stipple=stipple,
        )

    def set_battery(self, percent, is_charging=False, status_text=""):
        """Update the gauge with new battery data.

        Args:
            percent: Battery percentage (0-100).
            is_charging: Whether battery is charging.
            status_text: Status text to display.
        """
        self._target_percent = percent
        self._is_charging = is_charging
        self._status_text = status_text

        if not self._animating:
            self._animate()

    def _animate(self):
        """Animate the gauge smoothly to target percentage."""
        self._animating = True
        diff = self._target_percent - self._percent

        if abs(diff) < 0.5:
            self._percent = self._target_percent
            self._draw_gauge()
            self._animating = False
            return

        # Smooth ease towards target
        self._percent += diff * 0.2
        self._draw_gauge()
        self.after(30, self._animate)  # ~33fps smooth animation without CPU churn


class InlineStat(ctk.CTkFrame):
    """A compact inline stat with label and value — no card boxing."""

    def __init__(self, master, label, value="...", color=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._color = color or Colors.ACCENT

        # Label
        ctk.CTkLabel(
            self,
            text=label,
            font=Fonts.CAPTION,
            text_color=Colors.TEXT_TERTIARY,
        ).pack(anchor="w")

        # Value
        self._value_label = ctk.CTkLabel(
            self,
            text=str(value),
            font=Fonts.HEADING_3,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        )
        self._value_label.pack(anchor="w", pady=(2, 0))

    def set_value(self, value):
        """Update the displayed value."""
        self._value_label.configure(text=str(value))

    def set_color(self, color):
        """Update the value color."""
        self._value_label.configure(text_color=color)


class DashboardView(ctk.CTkFrame):
    """Main dashboard view with hero battery gauge, inline stats, and Clean Sweep."""

    def __init__(self, master, battery_monitor, process_tracker, power_manager, **kwargs):
        super().__init__(master, fg_color=Colors.BG_PRIMARY, **kwargs)

        self._battery = battery_monitor
        self._process_tracker = process_tracker
        self._power_manager = power_manager
        self._update_job = None

        self._build_ui()
        self._start_updates()

    def _build_ui(self):
        """Construct the dashboard layout."""
        # Scrollable container
        container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=Colors.BG_ELEVATED,
            scrollbar_button_hover_color=Colors.BORDER_LIGHT,
        )
        container.pack(fill="both", expand=True, padx=20, pady=(14, 20))

        # ── Header ──────────────────────────────────────────────────
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            header,
            text="Dashboard",
            font=Fonts.HEADING_1,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        # Timestamp
        self._time_label = ctk.CTkLabel(
            header,
            text="",
            font=Fonts.CAPTION,
            text_color=Colors.TEXT_TERTIARY,
        )
        self._time_label.pack(side="right")

        # ── Hero Battery Gauge ──────────────────────────────────────
        gauge_section = ctk.CTkFrame(
            container,
            fg_color=Colors.BG_CARD,
            corner_radius=Dimensions.CARD_CORNER_RADIUS,
            border_width=1,
            border_color=Colors.BORDER,
        )
        gauge_section.pack(fill="x", pady=(6, Dimensions.SECTION_GAP))

        gauge_inner = ctk.CTkFrame(gauge_section, fg_color="transparent")
        gauge_inner.pack(fill="x", padx=20, pady=16)

        # Left: Gauge
        gauge_left = ctk.CTkFrame(gauge_inner, fg_color="transparent")
        gauge_left.pack(side="left")

        self._gauge = BatteryGauge(gauge_left, size=200)
        self._gauge.pack()

        # Right: Key metrics stacked vertically
        metrics_right = ctk.CTkFrame(gauge_inner, fg_color="transparent")
        metrics_right.pack(side="left", fill="both", expand=True, padx=(24, 0))

        # Time remaining
        self._time_remaining = ctk.CTkLabel(
            metrics_right,
            text="Estimating...",
            font=Fonts.HEADING_2,
            text_color=Colors.TEXT_PRIMARY,
        )
        self._time_remaining.pack(anchor="w", pady=(8, 2))

        ctk.CTkLabel(
            metrics_right,
            text="Estimated time remaining",
            font=Fonts.CAPTION,
            text_color=Colors.TEXT_TERTIARY,
        ).pack(anchor="w")

        # Thin divider
        ctk.CTkFrame(
            metrics_right,
            fg_color=Colors.BORDER,
            height=1,
        ).pack(fill="x", pady=10)

        # Inline stats row
        stats_row = ctk.CTkFrame(metrics_right, fg_color="transparent")
        stats_row.pack(fill="x")
        stats_row.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self._health_stat = InlineStat(stats_row, "Health", "...", Colors.SUCCESS)
        self._health_stat.grid(row=0, column=0, sticky="w")

        self._plan_stat = InlineStat(stats_row, "Power Plan", "...", Colors.ACCENT)
        self._plan_stat.grid(row=0, column=1, sticky="w")

        self._proc_stat = InlineStat(stats_row, "Processes", "0", Colors.WARNING)
        self._proc_stat.grid(row=0, column=2, sticky="w")

        self._mem_stat = InlineStat(stats_row, "Memory", "0 MB", Colors.ACCENT)
        self._mem_stat.grid(row=0, column=3, sticky="w")

        # ── Quick Actions ───────────────────────────────────────────
        action_section = ctk.CTkFrame(
            container,
            fg_color=Colors.BG_CARD,
            corner_radius=Dimensions.CARD_CORNER_RADIUS,
            border_width=1,
            border_color=Colors.BORDER,
        )
        action_section.pack(fill="x", pady=(0, Dimensions.SECTION_GAP))

        action_inner = ctk.CTkFrame(action_section, fg_color="transparent")
        action_inner.pack(fill="x", padx=20, pady=14)

        action_header = ctk.CTkFrame(action_inner, fg_color="transparent")
        action_header.pack(fill="x")

        ctk.CTkLabel(
            action_header,
            text="Quick Actions",
            font=Fonts.HEADING_3,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        self._sweep_status = ctk.CTkLabel(
            action_header,
            text="",
            font=Fonts.CAPTION,
            text_color=Colors.SUCCESS,
        )
        self._sweep_status.pack(side="right")

        ctk.CTkLabel(
            action_inner,
            text="Terminate all user-started processes in one click. System processes are protected.",
            font=Fonts.BODY_SMALL,
            text_color=Colors.TEXT_SECONDARY,
            wraplength=600,
            justify="left",
        ).pack(fill="x", pady=(6, 12), anchor="w")

        # Clean Sweep button — prominent but not overwhelming
        self._sweep_btn = ctk.CTkButton(
            action_inner,
            text="Clean Sweep — Kill All User Processes",
            font=Fonts.BUTTON,
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            height=42,
            corner_radius=Dimensions.BUTTON_CORNER_RADIUS,
            command=self._on_clean_sweep,
        )
        self._sweep_btn.pack(fill="x")

    def _start_updates(self):
        """Begin periodic UI updates."""
        self._update_dashboard()

    def _update_dashboard(self):
        """Refresh all dashboard data."""
        try:
            # Battery status
            status = self._battery.get_status()
            self._gauge.set_battery(
                percent=status["percent"],
                is_charging=status["plugged"],
                status_text=status["status"],
            )
            self._time_remaining.configure(
                text=status['time_left'] if status["time_left"] != "N/A" else "No Battery"
            )

            # Battery health
            health = self._battery.get_health()
            if health["available"]:
                h_pct = health["health_percent"]
                self._health_stat.set_value(f"{h_pct}%")
                self._health_stat.set_color(get_health_color(h_pct))
            else:
                self._health_stat.set_value("N/A")

            # Power plan
            plan = self._power_manager.get_active_plan()
            self._plan_stat.set_value(plan["name"])

            # Process count
            proc_count = self._process_tracker.get_process_count()
            self._proc_stat.set_value(str(proc_count))

            # Memory usage
            mem_mb = self._process_tracker.get_total_memory_mb()
            if mem_mb > 1024:
                self._mem_stat.set_value(f"{mem_mb / 1024:.1f} GB")
            else:
                self._mem_stat.set_value(f"{mem_mb:.0f} MB")

            # Timestamp
            now = time_mod.strftime("%H:%M:%S")
            self._time_label.configure(text=f"Updated {now}")

        except Exception:
            pass

        # Schedule next update only if mapped
        if self.winfo_ismapped():
            self._update_job = self.after(4000, self._update_dashboard)
        else:
            self._update_job = None

    def on_show(self):
        """Called when Dashboard becomes visible."""
        self._update_dashboard()

    def on_hide(self):
        """Called when switching away from Dashboard."""
        if self._update_job:
            self.after_cancel(self._update_job)
            self._update_job = None

    def _on_clean_sweep(self):
        """Handle Clean Sweep button click with confirmation dialog."""
        if hasattr(self, "_sweep_dialog") and self._sweep_dialog is not None:
            try:
                if self._sweep_dialog.winfo_exists():
                    self._sweep_dialog.focus()
                    return
            except Exception:
                pass

        proc_count = self._process_tracker.get_process_count()

        if proc_count == 0:
            self._sweep_status.configure(
                text="No user processes to clean",
                text_color=Colors.TEXT_SECONDARY,
            )
            return

        # Confirmation dialog
        dialog = ctk.CTkToplevel(self)
        self._sweep_dialog = dialog
        dialog.title("Clean Sweep Confirmation")
        dialog.geometry("420x210")
        dialog.resizable(False, False)
        dialog.configure(fg_color=Colors.BG_PRIMARY)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        # Center on parent
        try:
            dialog.update_idletasks()
            x = self.winfo_toplevel().winfo_x() + (self.winfo_toplevel().winfo_width() // 2) - 210
            y = self.winfo_toplevel().winfo_y() + (self.winfo_toplevel().winfo_height() // 2) - 105
            dialog.geometry(f"+{x}+{y}")
        except Exception:
            pass

        inner = ctk.CTkFrame(dialog, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=18)

        ctk.CTkLabel(
            inner,
            text=f"Confirm Clean Sweep",
            font=Fonts.HEADING_2,
            text_color=Colors.WARNING,
        ).pack(anchor="w")

        ctk.CTkLabel(
            inner,
            text=f"This will terminate {proc_count} user-started process{'es' if proc_count != 1 else ''}.\n"
                 f"System processes (explorer, services) are protected.\n"
                 f"Unsaved work in those applications may be lost.",
            font=Fonts.BODY,
            text_color=Colors.TEXT_SECONDARY,
            justify="left",
            wraplength=370,
        ).pack(anchor="w", pady=(8, 14))

        btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btn_frame.pack(fill="x")

        def confirm():
            dialog.destroy()
            self._execute_sweep()

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            font=Fonts.BODY_BOLD,
            fg_color=Colors.BG_ELEVATED,
            hover_color=Colors.BORDER_LIGHT,
            text_color=Colors.TEXT_PRIMARY,
            width=100,
            height=36,
            corner_radius=8,
            command=dialog.destroy,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame,
            text=f"Kill {proc_count} Process{'es' if proc_count != 1 else ''}",
            font=Fonts.BODY_BOLD,
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            width=160,
            height=36,
            corner_radius=8,
            command=confirm,
        ).pack(side="right")

    def _execute_sweep(self):
        """Execute the clean sweep operation in a background thread."""
        self._sweep_btn.configure(
            text="Cleaning user processes...",
            state="disabled",
            fg_color=Colors.BG_ELEVATED,
        )
        self._sweep_status.configure(
            text="Closing background apps...",
            text_color=Colors.ACCENT,
        )

        def bg_worker():
            killed = self._process_tracker.clean_sweep()
            self.after(0, lambda: self._on_sweep_done(killed))

        threading.Thread(target=bg_worker, daemon=True).start()

    def _on_sweep_done(self, killed):
        """Handle sweep completion on GUI thread."""
        self._sweep_btn.configure(
            text="Clean Sweep — Kill All User Processes",
            state="normal",
            fg_color=Colors.DANGER,
        )

        self._sweep_status.configure(
            text=f"Cleaned {killed} process{'es' if killed != 1 else ''}",
            text_color=Colors.SUCCESS,
        )

        # Clear status after 5 seconds and update counts
        self.after(5000, lambda: self._sweep_status.configure(text=""))
        self._update_dashboard()

    def destroy(self):
        """Clean up scheduled updates on destroy."""
        if self._update_job:
            self.after_cancel(self._update_job)
        super().destroy()
