"""
Settings view for PowerPilot.
Manages app preferences: autorun, theme, process exclusions, and about info.
"""

import customtkinter as ctk

from ui.theme import Colors, Fonts, Dimensions


class SettingToggle(ctk.CTkFrame):
    """A toggle switch setting with label and description."""

    def __init__(self, master, label, description, initial_value, on_change, **kwargs):
        super().__init__(
            master,
            fg_color=Colors.BG_CARD,
            corner_radius=Dimensions.CARD_CORNER_RADIUS,
            border_width=1,
            border_color=Colors.BORDER,
            cursor="hand2",
            **kwargs,
        )

        self._on_change = on_change

        inner = ctk.CTkFrame(self, fg_color="transparent", cursor="hand2")
        inner.pack(fill="both", expand=True, padx=20, pady=14)

        # Left: text
        text_frame = ctk.CTkFrame(inner, fg_color="transparent", cursor="hand2")
        text_frame.pack(side="left", fill="x", expand=True)

        lbl = ctk.CTkLabel(
            text_frame,
            text=label,
            font=Fonts.HEADING_3,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
            cursor="hand2",
        )
        lbl.pack(anchor="w")

        desc_lbl = ctk.CTkLabel(
            text_frame,
            text=description,
            font=Fonts.CAPTION,
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            cursor="hand2",
        )
        desc_lbl.pack(anchor="w", pady=(2, 0))

        # Right: switch
        self._switch_var = ctk.BooleanVar(value=initial_value)
        self._switch = ctk.CTkSwitch(
            inner,
            text="",
            variable=self._switch_var,
            onvalue=True,
            offvalue=False,
            fg_color=Colors.BG_ELEVATED,
            progress_color=Colors.ACCENT_DARK,
            button_color=Colors.TEXT_PRIMARY,
            button_hover_color=Colors.ACCENT,
            command=self._handle_change,
            width=46,
        )
        self._switch.pack(side="right", padx=(12, 0))

        # Card-level click to toggle
        def toggle_click(event=None):
            self._switch_var.set(not self._switch_var.get())
            self._handle_change()

        for w in (self, inner, text_frame, lbl, desc_lbl):
            w.bind("<Button-1>", toggle_click)
            w.bind("<Enter>", lambda e: self.configure(fg_color=Colors.BG_CARD_HOVER))
            w.bind("<Leave>", lambda e: self.configure(fg_color=Colors.BG_CARD))

    def _handle_change(self):
        self._on_change(self._switch_var.get())

    def set_value(self, value):
        self._switch_var.set(value)


class SettingsView(ctk.CTkFrame):
    """Settings panel for PowerPilot."""

    def __init__(self, master, config_manager, autorun_manager, **kwargs):
        super().__init__(master, fg_color=Colors.BG_PRIMARY, **kwargs)

        self._config = config_manager
        self._autorun = autorun_manager

        self._build_ui()

    def _build_ui(self):
        """Build the settings UI."""
        container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=Colors.BG_ELEVATED,
            scrollbar_button_hover_color=Colors.BORDER_LIGHT,
        )
        container.pack(fill="both", expand=True, padx=24, pady=(16, 24))

        # ── Header ──────────────────────────────────────────────────
        ctk.CTkLabel(
            container,
            text="Settings",
            font=Fonts.HEADING_1,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, Dimensions.SECTION_GAP))

        # ── General Section ─────────────────────────────────────────
        self._section_label(container, "⚙️  General")

        # Autorun toggle
        self._autorun_toggle = SettingToggle(
            container,
            label="Start with Windows",
            description="Launch PowerPilot automatically when you sign in",
            initial_value=self._autorun.is_enabled(),
            on_change=self._toggle_autorun,
        )
        self._autorun_toggle.pack(fill="x", pady=(8, 6))

        # Start minimized
        SettingToggle(
            container,
            label="Start Minimized",
            description="Start PowerPilot minimized to the taskbar",
            initial_value=self._config.get("start_minimized", False),
            on_change=lambda v: self._config.set("start_minimized", v),
        ).pack(fill="x", pady=6)

        # ── Process Exclusions ──────────────────────────────────────
        self._section_label(container, "📋  Process Exclusions")

        excl_card = ctk.CTkFrame(
            container,
            fg_color=Colors.BG_CARD,
            corner_radius=Dimensions.CARD_CORNER_RADIUS,
            border_width=1,
            border_color=Colors.BORDER,
        )
        excl_card.pack(fill="x", pady=(8, 6))

        excl_inner = ctk.CTkFrame(excl_card, fg_color="transparent")
        excl_inner.pack(fill="x", padx=20, pady=14)

        ctk.CTkLabel(
            excl_inner,
            text="Excluded Processes",
            font=Fonts.HEADING_3,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            excl_inner,
            text="Processes listed here will not appear in the tracker and won't be affected by Clean Sweep.",
            font=Fonts.CAPTION,
            text_color=Colors.TEXT_SECONDARY,
            wraplength=600,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(2, 12))

        # Exclusion input row
        input_row = ctk.CTkFrame(excl_inner, fg_color="transparent")
        input_row.pack(fill="x")

        self._excl_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Enter process name (e.g. spotify.exe)",
            font=Fonts.BODY,
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY,
            placeholder_text_color=Colors.TEXT_TERTIARY,
            height=38,
            corner_radius=8,
        )
        self._excl_entry.pack(side="left", fill="x", expand=True)
        self._excl_entry.bind("<Return>", lambda e: self._add_exclusion())

        ctk.CTkButton(
            input_row,
            text="+ Add",
            font=Fonts.BODY_BOLD,
            fg_color=Colors.ACCENT_DARK,
            hover_color=Colors.ACCENT,
            text_color=Colors.TEXT_PRIMARY,
            width=80,
            height=38,
            corner_radius=8,
            command=self._add_exclusion,
        ).pack(side="right", padx=(8, 0))

        # Exclusion list
        self._excl_list_frame = ctk.CTkFrame(excl_inner, fg_color="transparent")
        self._excl_list_frame.pack(fill="x", pady=(12, 0))
        self._render_exclusions()

        # ── About Section ───────────────────────────────────────────
        self._section_label(container, "ℹ️  About")

        about_card = ctk.CTkFrame(
            container,
            fg_color=Colors.BG_CARD,
            corner_radius=Dimensions.CARD_CORNER_RADIUS,
            border_width=1,
            border_color=Colors.BORDER,
        )
        about_card.pack(fill="x", pady=(8, 6))

        about_inner = ctk.CTkFrame(about_card, fg_color="transparent")
        about_inner.pack(fill="x", padx=20, pady=14)

        ctk.CTkLabel(
            about_inner,
            text="PowerPilot",
            font=Fonts.HEADING_2,
            text_color=Colors.ACCENT,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            about_inner,
            text="Battery optimization & process management for Windows 11.\n"
                 "Extend your battery life with smart power profiles and one-click cleanup.",
            font=Fonts.BODY_SMALL,
            text_color=Colors.TEXT_TERTIARY,
            wraplength=600,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(8, 0))

        # ── Reset Section ───────────────────────────────────────────
        self._section_label(container, "🔄  Reset")

        reset_card = ctk.CTkFrame(
            container,
            fg_color=Colors.BG_CARD,
            corner_radius=Dimensions.CARD_CORNER_RADIUS,
            border_width=1,
            border_color=Colors.BORDER,
        )
        reset_card.pack(fill="x", pady=(8, 6))

        reset_inner = ctk.CTkFrame(reset_card, fg_color="transparent")
        reset_inner.pack(fill="x", padx=20, pady=14)

        ctk.CTkLabel(
            reset_inner,
            text="Reset All Settings",
            font=Fonts.HEADING_3,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            reset_inner,
            text="Restore all settings to their default values. This cannot be undone.",
            font=Fonts.CAPTION,
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        ).pack(anchor="w", pady=(2, 12))

        ctk.CTkButton(
            reset_inner,
            text="Reset to Defaults",
            font=Fonts.BODY_BOLD,
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            width=160,
            height=38,
            corner_radius=8,
            command=self._reset_settings,
        ).pack(anchor="w")

        # Status label
        self._status_label = ctk.CTkLabel(
            container,
            text="",
            font=Fonts.CAPTION,
            text_color=Colors.SUCCESS,
        )
        self._status_label.pack(fill="x", pady=(12, 0))

    def _section_label(self, parent, text):
        """Create a section header label."""
        ctk.CTkLabel(
            parent,
            text=text,
            font=Fonts.HEADING_3,
            text_color=Colors.TEXT_SECONDARY,
        ).pack(anchor="w", pady=(Dimensions.SECTION_GAP, 4))

    def _toggle_autorun(self, enabled):
        """Handle autorun toggle."""
        success = self._autorun.set_enabled(enabled)
        self._config.set("autorun", enabled)
        if success:
            status = "enabled" if enabled else "disabled"
            self._show_status(f"✓ Autorun {status}")
        else:
            self._show_status("✗ Failed to update autorun", Colors.DANGER)

    def _add_exclusion(self):
        """Add a process to the exclusion list."""
        name = self._excl_entry.get().strip()
        if not name:
            return

        excluded = self._config.get("excluded_processes", [])
        if name.lower() not in [e.lower() for e in excluded]:
            excluded.append(name)
            self._config.set("excluded_processes", excluded)
            self._excl_entry.delete(0, "end")
            self._render_exclusions()
            self._show_status(f"✓ Added '{name}' to exclusions")
        else:
            self._show_status(f"'{name}' is already excluded", Colors.WARNING)

    def _remove_exclusion(self, name):
        """Remove a process from the exclusion list."""
        excluded = self._config.get("excluded_processes", [])
        excluded = [e for e in excluded if e.lower() != name.lower()]
        self._config.set("excluded_processes", excluded)
        self._render_exclusions()
        self._show_status(f"✓ Removed '{name}' from exclusions")

    def _render_exclusions(self):
        """Render the exclusion list chips."""
        for widget in self._excl_list_frame.winfo_children():
            widget.destroy()

        excluded = self._config.get("excluded_processes", [])

        if not excluded:
            ctk.CTkLabel(
                self._excl_list_frame,
                text="No excluded processes",
                font=Fonts.CAPTION,
                text_color=Colors.TEXT_TERTIARY,
            ).pack(anchor="w")
            return

        chips_frame = ctk.CTkFrame(self._excl_list_frame, fg_color="transparent")
        chips_frame.pack(fill="x")

        for name in excluded:
            chip = ctk.CTkFrame(
                chips_frame,
                fg_color=Colors.BG_ELEVATED,
                corner_radius=6,
            )
            chip.pack(side="left", padx=(0, 6), pady=2)

            ctk.CTkLabel(
                chip,
                text=f"  {name}",
                font=Fonts.CAPTION,
                text_color=Colors.TEXT_PRIMARY,
            ).pack(side="left", padx=(4, 0))

            ctk.CTkButton(
                chip,
                text="✕",
                font=("Segoe UI", 10),
                fg_color="transparent",
                hover_color=Colors.DANGER_BG,
                text_color=Colors.TEXT_TERTIARY,
                width=24,
                height=24,
                corner_radius=4,
                command=lambda n=name: self._remove_exclusion(n),
            ).pack(side="right")

    def _reset_settings(self):
        """Reset all settings to defaults."""
        self._config.reset()
        self._autorun.enable()  # Default is autorun enabled
        self._autorun_toggle.set_value(True)
        self._render_exclusions()
        self._show_status("✓ All settings reset to defaults")

    def _show_status(self, text, color=None):
        """Show a status message that auto-clears."""
        self._status_label.configure(
            text=text,
            text_color=color or Colors.SUCCESS,
        )
        self.after(4000, lambda: self._status_label.configure(text=""))
