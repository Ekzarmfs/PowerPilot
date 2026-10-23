"""
Loadout profiles view for PowerPilot.
Displays preset and custom loadout cards with one-click activation.
"""

import customtkinter as ctk
import threading

from ui.theme import Colors, Fonts, Dimensions


class LoadoutInspectDialog(ctk.CTkToplevel):
    """Inspection modal detailing what a loadout blocks and configures before applying."""

    _PLAN_DETAILS = {
        "balanced": ("Balanced Power Plan", "Balances CPU performance and energy efficiency dynamically based on load."),
        "high_performance": ("High Performance Power Plan", "Unthrottles CPU clock speeds and disables aggressive core parking for maximum speed."),
        "power_saver": ("Power Saver Power Plan", "Caps maximum CPU frequency and aggressively parks cores to minimize wattage."),
        "ultimate_performance": ("Ultimate Performance", "Zero power throttling for extreme workloads on high-end hardware."),
    }

    def __init__(self, master, loadout_key, loadout, on_confirm_apply):
        super().__init__(master)

        self._key = loadout_key
        self._loadout = loadout
        self._on_confirm_apply = on_confirm_apply
        self._clicked = False

        self.title(f"{loadout.icon} {loadout.name} — Loadout Inspection")
        self.geometry("520x540")
        self.minsize(460, 480)
        self.configure(fg_color=Colors.BG_PRIMARY)
        self.transient(master.winfo_toplevel())
        self.grab_set()

        # Center on parent window
        try:
            self.update_idletasks()
            pw = master.winfo_toplevel().winfo_width()
            ph = master.winfo_toplevel().winfo_height()
            px = master.winfo_toplevel().winfo_x()
            py = master.winfo_toplevel().winfo_y()
            x = max(0, px + (pw - 520) // 2)
            y = max(0, py + (ph - 540) // 2)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

        self._build_ui()

    def _build_ui(self):
        container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=Colors.BG_ELEVATED,
            scrollbar_button_hover_color=Colors.BORDER_LIGHT,
        )
        container.pack(fill="both", expand=True, padx=20, pady=(18, 14))

        # ── Header ──────────────────────────────────────────────────
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            header,
            text=self._loadout.icon,
            font=Fonts.ICON_LARGE,
        ).pack(side="left")

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", padx=(12, 0))

        ctk.CTkLabel(
            title_box,
            text=f"{self._loadout.name} Loadout",
            font=Fonts.HEADING_2,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="Review all restrictions and adjustments before applying",
            font=Fonts.TINY,
            text_color=Colors.TEXT_TERTIARY,
            anchor="w",
        ).pack(anchor="w")

        # Description
        desc_card = ctk.CTkFrame(
            container,
            fg_color=Colors.BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER,
        )
        desc_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            desc_card,
            text=self._loadout.description,
            font=Fonts.BODY,
            text_color=Colors.TEXT_SECONDARY,
            wraplength=440,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=14, pady=10)

        settings = self._loadout.settings

        # ── Section 1: What this loadout blocks ─────────────────────
        self._section_title(container, "What This Loadout Blocks", Colors.DANGER)

        blocked_items = []
        if settings.get("notifications") is False:
            blocked_items.append((
                "Windows Notifications",
                "Suppresses all toast notifications, banner popups, and focus alerts.",
            ))
        if settings.get("search_indexing") is False:
            blocked_items.append((
                "Windows Search Indexing",
                "Pauses SearchIndexer.exe background disk crawler.",
            ))
        if settings.get("bluetooth") is False:
            blocked_items.append((
                "Bluetooth Radios",
                "Turns off Bluetooth to eliminate wireless adapter drain.",
            ))
        if settings.get("kill_background"):
            blocked_items.append((
                "User Background Applications",
                "Closes non-essential user background apps to free RAM.",
            ))

        if blocked_items:
            for title, desc in blocked_items:
                row = ctk.CTkFrame(
                    container,
                    fg_color=Colors.BG_CARD,
                    corner_radius=6,
                    border_width=1,
                    border_color=Colors.DANGER_BG,
                )
                row.pack(fill="x", pady=2)

                inner = ctk.CTkFrame(row, fg_color="transparent")
                inner.pack(fill="x", padx=12, pady=8)

                ctk.CTkLabel(
                    inner,
                    text=title,
                    font=Fonts.BODY_BOLD,
                    text_color=Colors.DANGER,
                    anchor="w",
                ).pack(anchor="w")

                ctk.CTkLabel(
                    inner,
                    text=desc,
                    font=Fonts.TINY,
                    text_color=Colors.TEXT_SECONDARY,
                    wraplength=420,
                    justify="left",
                    anchor="w",
                ).pack(anchor="w", pady=(1, 0))
        else:
            none_card = ctk.CTkFrame(container, fg_color=Colors.BG_CARD, corner_radius=6)
            none_card.pack(fill="x", pady=2)
            ctk.CTkLabel(
                none_card,
                text="No services blocked by this profile",
                font=Fonts.BODY,
                text_color=Colors.SUCCESS,
            ).pack(padx=12, pady=8, anchor="w")

        # ── Section 2: System adjustments ──────────────────────────
        self._section_title(container, "System Adjustments", Colors.ACCENT)

        adj_items = []
        if "power_plan" in settings:
            plan = settings["power_plan"]
            plan_title, plan_desc = self._PLAN_DETAILS.get(
                plan,
                (f"{plan.title()} Power Plan", "Adjusts Windows power profile.")
            )
            adj_items.append((plan_title, plan_desc))

        if "brightness" in settings:
            b_val = settings["brightness"]
            b_desc = f"Sets screen backlight to {b_val}%. "
            if b_val <= 30:
                b_desc += "Significant power savings on battery."
            elif b_val >= 90:
                b_desc += "Optimized for maximum visual clarity."
            else:
                b_desc += "Balanced for comfortable indoor use."
            adj_items.append((f"Display Brightness: {b_val}%", b_desc))

        for title, desc in adj_items:
            row = ctk.CTkFrame(
                container,
                fg_color=Colors.BG_CARD,
                corner_radius=6,
                border_width=1,
                border_color=Colors.BORDER,
            )
            row.pack(fill="x", pady=2)

            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=12, pady=8)

            ctk.CTkLabel(
                inner,
                text=title,
                font=Fonts.BODY_BOLD,
                text_color=Colors.ACCENT,
                anchor="w",
            ).pack(anchor="w")

            ctk.CTkLabel(
                inner,
                text=desc,
                font=Fonts.TINY,
                text_color=Colors.TEXT_SECONDARY,
                wraplength=420,
                justify="left",
                anchor="w",
            ).pack(anchor="w", pady=(1, 0))

        # ── Safety Notice ───────────────────────────────────────────
        safety = ctk.CTkFrame(
            container,
            fg_color=Colors.SUCCESS_BG,
            corner_radius=6,
            border_width=1,
            border_color=Colors.SUCCESS_BG,
        )
        safety.pack(fill="x", pady=(10, 6))

        ctk.CTkLabel(
            safety,
            text="Safe & Fully Reversible\n"
                 "System processes are protected and never touched. "
                 "Deactivate any time to restore defaults.",
            font=Fonts.TINY,
            text_color=Colors.SUCCESS,
            wraplength=430,
            justify="left",
        ).pack(fill="x", padx=12, pady=8)

        # ── Bottom action buttons ───────────────────────────────────
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkButton(
            btn_bar,
            text="Cancel",
            font=Fonts.BODY,
            fg_color=Colors.BG_ELEVATED,
            hover_color=Colors.BORDER_LIGHT,
            text_color=Colors.TEXT_PRIMARY,
            width=90,
            height=34,
            corner_radius=6,
            command=self.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            btn_bar,
            text=f"Apply {self._loadout.name} Profile",
            font=Fonts.BODY_BOLD,
            fg_color=Colors.ACCENT_DARK,
            hover_color=Colors.ACCENT,
            text_color=Colors.TEXT_PRIMARY,
            height=34,
            corner_radius=6,
            command=self._confirm,
        ).pack(side="right", fill="x", expand=True, padx=(10, 0))

    def _section_title(self, parent, text, color):
        ctk.CTkLabel(
            parent,
            text=text,
            font=Fonts.BODY_BOLD,
            text_color=color,
            anchor="w",
        ).pack(anchor="w", pady=(10, 3))

    def _confirm(self):
        if self._clicked:
            return
        self._clicked = True
        self.destroy()
        self._on_confirm_apply(self._key)


class LoadoutCard(ctk.CTkFrame):
    """A loadout profile card with description and activation controls."""

    _PLAN_LABELS = {
        "balanced": "Balanced",
        "high_performance": "High Performance",
        "power_saver": "Power Saver",
        "ultimate_performance": "Ultimate",
    }

    def __init__(self, master, key, loadout, is_active, on_activate, on_deactivate, **kwargs):
        super().__init__(
            master,
            fg_color=Colors.BG_CARD,
            corner_radius=Dimensions.CARD_CORNER_RADIUS,
            border_width=2 if is_active else 1,
            border_color=Colors.ACCENT if is_active else Colors.BORDER,
            **kwargs,
        )

        self._key = key
        self._loadout = loadout
        self._is_active = is_active
        self._on_activate = on_activate
        self._on_deactivate = on_deactivate
        self._click_locked = False

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=14)

        # ── Header: Icon + Name + Active badge ──────────────────────
        header = ctk.CTkFrame(inner, fg_color="transparent")
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text=loadout.icon,
            font=Fonts.ICON_LARGE,
        ).pack(side="left")

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=(10, 0), fill="x", expand=True)

        ctk.CTkLabel(
            title_frame,
            text=loadout.name,
            font=Fonts.HEADING_2,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w")

        if is_active:
            status_chip = ctk.CTkLabel(
                header,
                text="  Active  ",
                font=Fonts.CAPTION_BOLD,
                text_color=Colors.ACCENT,
                fg_color=Colors.ACCENT_SUBTLE,
                corner_radius=4,
            )
            status_chip.pack(side="right")

        # ── Description ─────────────────────────────────────────────
        ctk.CTkLabel(
            inner,
            text=loadout.description,
            font=Fonts.BODY_SMALL,
            text_color=Colors.TEXT_SECONDARY,
            wraplength=320,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(8, 8), anchor="w")

        settings = loadout.settings

        # ── Blocked & Settings Tags ─────────────────────────────────
        tags_frame = ctk.CTkFrame(inner, fg_color="transparent")
        tags_frame.pack(fill="x", pady=(0, 8), anchor="w")

        blocked_tags = []
        if settings.get("notifications") is False:
            blocked_tags.append("Notifications Off")
        if settings.get("search_indexing") is False:
            blocked_tags.append("Search Paused")
        if settings.get("bluetooth") is False:
            blocked_tags.append("Bluetooth Off")
        if settings.get("kill_background"):
            blocked_tags.append("Background Apps Closed")

        for tag in blocked_tags:
            ctk.CTkLabel(
                tags_frame,
                text=f"  {tag}  ",
                font=Fonts.TINY,
                text_color=Colors.DANGER,
                fg_color=Colors.DANGER_BG,
                corner_radius=3,
                pady=1,
            ).pack(side="left", padx=(0, 4), pady=1)

        if "power_plan" in settings:
            plan_str = self._PLAN_LABELS.get(
                settings["power_plan"],
                settings["power_plan"].title(),
            )
            ctk.CTkLabel(
                tags_frame,
                text=f"  {plan_str}  ",
                font=Fonts.TINY,
                text_color=Colors.ACCENT,
                fg_color=Colors.BG_ELEVATED,
                corner_radius=3,
                pady=1,
            ).pack(side="left", padx=(0, 4))

        if "brightness" in settings:
            ctk.CTkLabel(
                tags_frame,
                text=f"  {settings['brightness']}% Brightness  ",
                font=Fonts.TINY,
                text_color=Colors.TEXT_SECONDARY,
                fg_color=Colors.BG_ELEVATED,
                corner_radius=3,
                pady=1,
            ).pack(side="left", padx=(0, 4))

        # ── Action Buttons ──────────────────────────────────────────
        action_row = ctk.CTkFrame(inner, fg_color="transparent")
        action_row.pack(fill="x", pady=(4, 0))

        if is_active:
            btn = ctk.CTkButton(
                action_row,
                text="Active — Click to Deactivate",
                font=Fonts.BODY_BOLD,
                fg_color=Colors.ACCENT_SUBTLE,
                hover_color=Colors.BG_ELEVATED,
                text_color=Colors.ACCENT,
                height=36,
                corner_radius=6,
                border_width=1,
                border_color=Colors.ACCENT,
                command=self._handle_deactivate,
            )
            btn.pack(fill="x")
        else:
            # Inspection + Apply
            ctk.CTkButton(
                action_row,
                text="What It Blocks",
                font=Fonts.BODY,
                fg_color=Colors.BG_ELEVATED,
                hover_color=Colors.BORDER_LIGHT,
                text_color=Colors.TEXT_PRIMARY,
                height=34,
                corner_radius=6,
                command=self._open_inspect_dialog,
            ).pack(side="left", fill="x", expand=True, padx=(0, 4))

            ctk.CTkButton(
                action_row,
                text="Apply",
                font=Fonts.BODY_BOLD,
                fg_color=Colors.ACCENT_DARK,
                hover_color=Colors.ACCENT,
                text_color=Colors.TEXT_PRIMARY,
                height=34,
                corner_radius=6,
                command=self._open_inspect_dialog,
            ).pack(side="right", fill="x", expand=True, padx=(4, 0))

        # Hover and double click effects
        self.configure(cursor="hand2")
        self.bind("<Double-Button-1>", lambda e: self._open_inspect_dialog())
        inner.bind("<Double-Button-1>", lambda e: self._open_inspect_dialog())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _open_inspect_dialog(self):
        """Open the modal inspection dialog."""
        LoadoutInspectDialog(
            master=self,
            loadout_key=self._key,
            loadout=self._loadout,
            on_confirm_apply=self._handle_activate,
        )

    def _handle_activate(self, key):
        if self._click_locked:
            return
        self._click_locked = True
        self.after(300, self._unlock_click)
        self._on_activate(key)

    def _handle_deactivate(self):
        if self._click_locked:
            return
        self._click_locked = True
        self.after(300, self._unlock_click)
        self._on_deactivate()

    def _unlock_click(self):
        self._click_locked = False

    def _on_enter(self, event=None):
        if not self._is_active:
            self.configure(
                fg_color=Colors.BG_CARD_HOVER,
                border_color=Colors.BORDER_LIGHT,
            )

    def _on_leave(self, event=None):
        if not self._is_active:
            self.configure(
                fg_color=Colors.BG_CARD,
                border_color=Colors.BORDER,
            )


class LoadoutsView(ctk.CTkFrame):
    """Loadout profiles view with grid of loadout cards."""

    def __init__(self, master, loadout_manager, **kwargs):
        super().__init__(master, fg_color=Colors.BG_PRIMARY, **kwargs)

        self._loadout_manager = loadout_manager
        self._build_ui()

    def _build_ui(self):
        """Build the loadouts view."""
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
        header.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            header,
            text="Loadout Profiles",
            font=Fonts.HEADING_1,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        self._active_label = ctk.CTkLabel(
            header,
            text="",
            font=Fonts.BODY_SMALL,
            text_color=Colors.ACCENT,
        )
        self._active_label.pack(side="right")

        ctk.CTkLabel(
            self._container,
            text="Choose a profile to instantly optimize your system. "
                 "Each loadout adjusts power plan, notifications, brightness, and more.",
            font=Fonts.BODY_SMALL,
            text_color=Colors.TEXT_SECONDARY,
            wraplength=700,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(0, Dimensions.SECTION_GAP), anchor="w")

        # ── Status bar ──────────────────────────────────────────────
        self._status_label = ctk.CTkLabel(
            self._container,
            text="",
            font=Fonts.BODY_SMALL,
            text_color=Colors.SUCCESS,
        )
        self._status_label.pack(fill="x", pady=(0, 8))

        # ── Cards grid ──────────────────────────────────────────────
        self._cards_frame = ctk.CTkFrame(self._container, fg_color="transparent")
        self._cards_frame.pack(fill="both", expand=True)

        self._render_cards()

    def _render_cards(self):
        """Render all loadout cards in a 2-column grid."""
        # Clear existing cards
        for widget in self._cards_frame.winfo_children():
            widget.destroy()

        self._cards_frame.grid_columnconfigure((0, 1), weight=1)

        all_loadouts = self._loadout_manager.get_all_loadouts()
        active_key = self._loadout_manager.get_active_loadout_key()

        # Update active label
        if active_key and active_key in all_loadouts:
            active_loadout = all_loadouts[active_key]
            self._active_label.configure(
                text=f"{active_loadout.icon} {active_loadout.name} Active"
            )
        else:
            self._active_label.configure(text="No loadout active")

        row = 0
        col = 0
        for key, loadout in all_loadouts.items():
            card = LoadoutCard(
                self._cards_frame,
                key=key,
                loadout=loadout,
                is_active=(key == active_key),
                on_activate=self._activate_loadout,
                on_deactivate=self._deactivate_loadout,
            )
            card.grid(
                row=row, column=col,
                sticky="nsew",
                padx=(0 if col == 0 else 4, 4 if col == 0 else 0),
                pady=4,
            )

            col += 1
            if col >= 2:
                col = 0
                row += 1

    def _activate_loadout(self, key):
        """Activate a loadout profile asynchronously."""
        loadout = self._loadout_manager.get_loadout(key)
        if not loadout:
            return

        self._status_label.configure(
            text=f"Applying {loadout.icon} {loadout.name} profile...",
            text_color=Colors.ACCENT,
        )

        def worker():
            results = self._loadout_manager.apply_loadout(key)
            self.after(0, lambda: self._on_activate_done(loadout, results))

        threading.Thread(target=worker, daemon=True).start()

    def _on_activate_done(self, loadout, results):
        """Handle loadout activation finish on GUI thread."""
        if results is not False:
            self._status_label.configure(
                text=f"{loadout.icon} {loadout.name} activated successfully!",
                text_color=Colors.SUCCESS,
            )
        else:
            self._status_label.configure(
                text=f"Failed to activate {loadout.name}",
                text_color=Colors.DANGER,
            )
        self._render_cards()
        self.after(5000, lambda: self._status_label.configure(text=""))

    def _deactivate_loadout(self):
        """Deactivate the current loadout asynchronously."""
        self._status_label.configure(
            text="Restoring default system settings...",
            text_color=Colors.ACCENT,
        )

        def worker():
            self._loadout_manager.deactivate()
            self.after(0, self._on_deactivate_done)

        threading.Thread(target=worker, daemon=True).start()

    def _on_deactivate_done(self):
        """Handle deactivation finish on GUI thread."""
        self._status_label.configure(
            text="Loadout deactivated — defaults restored",
            text_color=Colors.TEXT_SECONDARY,
        )
        self._render_cards()
        self.after(5000, lambda: self._status_label.configure(text=""))
