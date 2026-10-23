"""
Main application window for PowerPilot.
Implements the sidebar navigation and page switching between views.
"""

import customtkinter as ctk

from ui.theme import Colors, Fonts, Dimensions
from ui.dashboard import DashboardView
from ui.processes import ProcessesView
from ui.loadouts_view import LoadoutsView
from ui.optimizer import OptimizerView
from ui.faq import FAQView
from ui.settings import SettingsView

from core.battery import BatteryMonitor
from core.process_tracker import ProcessTracker
from core.power_manager import PowerManager
from core.loadouts import LoadoutManager
from core.notifications import NotificationManager
from core.autorun import AutoRunManager
from core.bg_process_manager import BackgroundProcessManager
from config.config_manager import ConfigManager


class NavButton(ctk.CTkFrame):
    """A sidebar navigation button with icon, label, and active indicator bar."""

    def __init__(self, master, icon, label, is_active=False, command=None, **kwargs):
        super().__init__(
            master,
            fg_color=Colors.NAV_ACTIVE if is_active else "transparent",
            corner_radius=8,
            cursor="hand2",
            **kwargs,
        )

        self._command = command
        self._is_active = is_active
        self._click_locked = False

        # Active indicator bar — thin left accent line
        self._indicator = ctk.CTkFrame(
            self,
            fg_color=Colors.NAV_INDICATOR,
            width=3,
            corner_radius=2,
        )
        if is_active:
            self._indicator.place(x=0, rely=0.15, relheight=0.7)

        inner = ctk.CTkFrame(self, fg_color="transparent", cursor="hand2")
        inner.pack(fill="x", padx=10, pady=8)

        # Icon — smaller, subdued
        self._icon_label = ctk.CTkLabel(
            inner,
            text=icon,
            font=Fonts.ICON_NAV,
            text_color=Colors.ACCENT if is_active else Colors.TEXT_TERTIARY,
            cursor="hand2",
        )
        self._icon_label.pack(side="left")

        # Label
        self._text_label = ctk.CTkLabel(
            inner,
            text=f"  {label}",
            font=Fonts.NAV_LABEL,
            text_color=Colors.TEXT_PRIMARY if is_active else Colors.TEXT_SECONDARY,
            cursor="hand2",
        )
        self._text_label.pack(side="left")

        # Bind clicks to all widgets
        for w in (self, inner, self._icon_label, self._text_label):
            w.bind("<Button-1>", self._on_click)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def _on_click(self, event=None):
        if self._click_locked:
            return
        self._click_locked = True
        self.after(200, self._unlock_click)
        if self._command:
            self._command()

    def _unlock_click(self):
        self._click_locked = False

    def _on_enter(self, event=None):
        if not self._is_active:
            self.configure(fg_color=Colors.NAV_HOVER)

    def _on_leave(self, event=None):
        if not self._is_active:
            self.configure(fg_color="transparent")

    def set_active(self, active):
        """Update the active state of this nav button."""
        self._is_active = active
        if active:
            self.configure(fg_color=Colors.NAV_ACTIVE)
            self._text_label.configure(text_color=Colors.TEXT_PRIMARY)
            self._icon_label.configure(text_color=Colors.ACCENT)
            self._indicator.place(x=0, rely=0.15, relheight=0.7)
        else:
            self.configure(fg_color="transparent")
            self._text_label.configure(text_color=Colors.TEXT_SECONDARY)
            self._icon_label.configure(text_color=Colors.TEXT_TERTIARY)
            self._indicator.place_forget()


class PowerPilotApp(ctk.CTk):
    """Main PowerPilot application window."""

    def __init__(self):
        super().__init__()

        # Window setup
        self.title("PowerPilot")
        self.geometry(f"{Dimensions.WINDOW_WIDTH}x{Dimensions.WINDOW_HEIGHT}")
        self.minsize(Dimensions.WINDOW_MIN_WIDTH, Dimensions.WINDOW_MIN_HEIGHT)
        self.configure(fg_color=Colors.BG_PRIMARY)

        # Set appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Try to set window icon
        try:
            self.iconbitmap(default="assets/icon.ico")
        except Exception:
            pass

        # Initialize core services
        self._init_services()

        # Build UI
        self._current_page = None
        self._nav_buttons = {}
        self._pages = {}
        self._build_ui()

        # Navigate to dashboard
        self._navigate("dashboard")

        # Setup autorun on first run
        self._first_run_setup()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _init_services(self):
        """Initialize all core service modules."""
        self.config_manager = ConfigManager()
        self.battery_monitor = BatteryMonitor()
        self.process_tracker = ProcessTracker()
        self.power_manager = PowerManager()
        self.notification_manager = NotificationManager()
        self.autorun_manager = AutoRunManager()
        self.bg_process_manager = BackgroundProcessManager()

        # Configure process exclusions from config
        excluded = self.config_manager.get("excluded_processes", [])
        self.process_tracker.set_excluded(excluded)

        # Initialize loadout manager with all services
        self.loadout_manager = LoadoutManager(
            power_manager=self.power_manager,
            notification_manager=self.notification_manager,
            process_tracker=self.process_tracker,
        )

        # Import custom loadouts from config
        custom_loadouts = self.config_manager.get("custom_loadouts", {})
        if custom_loadouts:
            self.loadout_manager.import_custom_loadouts(custom_loadouts)

        # Start background monitoring
        self.battery_monitor.start_monitoring(interval=5)
        self.process_tracker.start_tracking(interval=4)

    def _build_ui(self):
        """Build the main application layout."""
        # Main container
        self._main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._main_frame.pack(fill="both", expand=True)

        # ── Sidebar ─────────────────────────────────────────────────
        sidebar = ctk.CTkFrame(
            self._main_frame,
            fg_color=Colors.BG_SECONDARY,
            width=Dimensions.SIDEBAR_WIDTH,
            corner_radius=0,
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # App branding — compact, elegant
        brand_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=14, pady=(18, 4))

        ctk.CTkLabel(
            brand_frame,
            text="⚡",
            font=("Segoe UI Emoji", 20),
            text_color=Colors.ACCENT,
        ).pack(side="left")

        brand_text = ctk.CTkFrame(brand_frame, fg_color="transparent")
        brand_text.pack(side="left", padx=(8, 0))

        ctk.CTkLabel(
            brand_text,
            text="PowerPilot",
            font=("Segoe UI", 15, "bold"),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            brand_text,
            text="Battery Optimizer",
            font=Fonts.TINY,
            text_color=Colors.TEXT_TERTIARY,
        ).pack(anchor="w")

        # Thin divider
        ctk.CTkFrame(
            sidebar,
            fg_color=Colors.BORDER,
            height=1,
        ).pack(fill="x", padx=14, pady=(10, 12))

        # Navigation items — top group
        nav_items_top = [
            ("dashboard", "🏠", "Dashboard"),
            ("processes", "📊", "Processes"),
            ("optimizer", "🔋", "Optimizer"),
            ("loadouts", "🎯", "Loadouts"),
        ]

        nav_items_bottom = [
            ("faq", "❓", "FAQ"),
            ("settings", "⚙️", "Settings"),
        ]

        self._nav_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        self._nav_frame.pack(fill="x", padx=6)

        for key, icon, label in nav_items_top:
            btn = NavButton(
                self._nav_frame,
                icon=icon,
                label=label,
                command=lambda k=key: self._navigate(k),
            )
            btn.pack(fill="x", pady=1)
            self._nav_buttons[key] = btn

        # Bottom nav items — pushed to the bottom
        bottom_nav_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        bottom_nav_frame.pack(side="bottom", fill="x", padx=6, pady=(0, 14))

        # Thin divider above bottom nav
        ctk.CTkFrame(
            bottom_nav_frame,
            fg_color=Colors.BORDER,
            height=1,
        ).pack(fill="x", padx=8, pady=(0, 6))

        for key, icon, label in nav_items_bottom:
            btn = NavButton(
                bottom_nav_frame,
                icon=icon,
                label=label,
                command=lambda k=key: self._navigate(k),
            )
            btn.pack(fill="x", pady=1)
            self._nav_buttons[key] = btn

        # ── Content Area ────────────────────────────────────────────
        # Thin vertical separator
        ctk.CTkFrame(
            self._main_frame,
            fg_color=Colors.BORDER,
            width=1,
        ).pack(side="left", fill="y")

        self._content_frame = ctk.CTkFrame(
            self._main_frame,
            fg_color=Colors.BG_PRIMARY,
            corner_radius=0,
        )
        self._content_frame.pack(side="left", fill="both", expand=True)

        # Create all page views
        self._pages["dashboard"] = DashboardView(
            self._content_frame,
            battery_monitor=self.battery_monitor,
            process_tracker=self.process_tracker,
            power_manager=self.power_manager,
        )

        self._pages["processes"] = ProcessesView(
            self._content_frame,
            process_tracker=self.process_tracker,
        )

        self._pages["optimizer"] = OptimizerView(
            self._content_frame,
            bg_process_manager=self.bg_process_manager,
            process_tracker=self.process_tracker,
        )

        self._pages["loadouts"] = LoadoutsView(
            self._content_frame,
            loadout_manager=self.loadout_manager,
        )

        self._pages["settings"] = SettingsView(
            self._content_frame,
            config_manager=self.config_manager,
            autorun_manager=self.autorun_manager,
        )

        self._pages["faq"] = FAQView(
            self._content_frame,
        )

    def _navigate(self, page_key):
        """Switch to a different page view.

        Args:
            page_key: Key of the page to display.
        """
        if page_key == self._current_page:
            return

        # Hide current page and trigger on_hide lifecycle hook
        if self._current_page and self._current_page in self._pages:
            old_view = self._pages[self._current_page]
            if hasattr(old_view, "on_hide"):
                try:
                    old_view.on_hide()
                except Exception:
                    pass
            old_view.pack_forget()

        # Show new page and trigger on_show lifecycle hook
        if page_key in self._pages:
            new_view = self._pages[page_key]
            new_view.pack(fill="both", expand=True)
            if hasattr(new_view, "on_show"):
                try:
                    new_view.on_show()
                except Exception:
                    pass

        # Update nav button states
        for key, btn in self._nav_buttons.items():
            btn.set_active(key == page_key)

        self._current_page = page_key

    def _first_run_setup(self):
        """Handle first-run initialization."""
        if self.config_manager.get("first_run", True):
            # Enable autorun by default
            self.autorun_manager.enable()
            self.config_manager.set("first_run", False)

    def _on_close(self):
        """Handle window close event."""
        # Save config
        self.config_manager.set(
            "custom_loadouts",
            self.loadout_manager.export_custom_loadouts(),
        )
        self.config_manager.save()

        # Stop monitoring
        self.battery_monitor.stop_monitoring()
        self.process_tracker.stop_tracking()

        self.destroy()

    def run(self):
        """Start the application main loop."""
        self.mainloop()
