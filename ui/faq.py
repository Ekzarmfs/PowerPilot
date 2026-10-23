"""
FAQ view for PowerPilot.
Provides answers about what the app does, privacy, data handling, and safety.
"""

import customtkinter as ctk

from ui.theme import Colors, Fonts, Dimensions


class FAQItem(ctk.CTkFrame):
    """An expandable FAQ accordion item styled like a unified Windows 11 Fluent expander."""

    def __init__(self, master, icon, question, answer, accent_color=None, **kwargs):
        super().__init__(
            master,
            fg_color=Colors.BG_CARD,
            corner_radius=Dimensions.CARD_CORNER_RADIUS,
            border_width=1,
            border_color=Colors.BORDER,
            **kwargs,
        )

        self._expanded = False
        self._click_locked = False
        self._accent = accent_color or Colors.ACCENT

        # ── Question Header (always visible) ───────────────────────────
        self._header_frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
            corner_radius=Dimensions.CARD_CORNER_RADIUS - 2,
            cursor="hand2",
        )
        self._header_frame.pack(fill="x", padx=4, pady=4)

        header_inner = ctk.CTkFrame(self._header_frame, fg_color="transparent", cursor="hand2")
        header_inner.pack(fill="x", padx=16, pady=12)

        # Icon
        self._icon_label = ctk.CTkLabel(
            header_inner,
            text=icon,
            font=("Segoe UI Emoji", 16),
            cursor="hand2",
        )
        self._icon_label.pack(side="left")

        # Question text
        self._q_label = ctk.CTkLabel(
            header_inner,
            text=f"  {question}",
            font=Fonts.HEADING_3,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
            cursor="hand2",
        )
        self._q_label.pack(side="left", fill="x", expand=True)

        # Expand arrow
        self._arrow = ctk.CTkLabel(
            header_inner,
            text="▶",
            font=Fonts.BODY_BOLD,
            text_color=Colors.TEXT_TERTIARY,
            cursor="hand2",
        )
        self._arrow.pack(side="right")

        # ── Separator Divider (hidden when collapsed) ─────────────────
        self._divider = ctk.CTkFrame(
            self,
            fg_color=Colors.BORDER,
            height=1,
        )

        # ── Answer Container (hidden when collapsed) ───────────────────
        self._answer_container = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )

        answer_inner = ctk.CTkFrame(
            self._answer_container,
            fg_color=Colors.BG_PRIMARY,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER,
        )
        answer_inner.pack(fill="x", padx=16, pady=(10, 16))

        answer_content = ctk.CTkFrame(answer_inner, fg_color="transparent")
        answer_content.pack(fill="x", padx=16, pady=14)

        # Left accent vertical bar
        ctk.CTkFrame(
            answer_content,
            fg_color=self._accent,
            width=3,
            corner_radius=2,
        ).pack(side="left", fill="y", padx=(0, 14))

        # Answer text
        self._ans_label = ctk.CTkLabel(
            answer_content,
            text=answer,
            font=Fonts.BODY,
            text_color=Colors.TEXT_SECONDARY,
            wraplength=640,
            justify="left",
            anchor="nw",
        )
        self._ans_label.pack(side="left", fill="x", expand=True)

        # Bind clicks to all header elements
        for w in (self._header_frame, header_inner, self._icon_label, self._q_label, self._arrow):
            w.bind("<Button-1>", self._on_click)
            w.bind("<Enter>", self._on_header_enter)
            w.bind("<Leave>", self._on_header_leave)

        # Responsive wrap adjustment
        self.bind("<Configure>", self._on_configure)

    def _on_configure(self, event):
        """Keep answer text responsive to parent container width."""
        try:
            available_w = event.width - 90
            if available_w > 200:
                self._ans_label.configure(wraplength=available_w)
        except Exception:
            pass

    def _on_header_enter(self, event=None):
        self._header_frame.configure(fg_color=Colors.NAV_HOVER)

    def _on_header_leave(self, event=None):
        self._header_frame.configure(fg_color="transparent")

    def _on_click(self, event=None):
        """Debounced click to prevent double-click jitter."""
        if self._click_locked:
            return
        self._click_locked = True
        self.after(200, self._unlock_click)
        self._toggle()

    def _unlock_click(self):
        self._click_locked = False

    def _toggle(self):
        """Toggle answer view with clean visual feedback."""
        self._expanded = not self._expanded
        if self._expanded:
            self._divider.pack(fill="x", padx=16)
            self._answer_container.pack(fill="x")
            self._arrow.configure(text="▼", text_color=self._accent)
            self.configure(border_color=self._accent)
        else:
            self._answer_container.pack_forget()
            self._divider.pack_forget()
            self._arrow.configure(text="▶", text_color=Colors.TEXT_TERTIARY)
            self.configure(border_color=Colors.BORDER)


class FAQView(ctk.CTkFrame):
    """FAQ page with categorized questions and answers."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=Colors.BG_PRIMARY, **kwargs)
        self._build_ui()

    def _build_ui(self):
        """Build the FAQ page UI."""
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
            text="Frequently Asked Questions",
            font=Fonts.HEADING_1,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 4))

        ctk.CTkLabel(
            container,
            text="Everything you need to know about PowerPilot — "
                 "how it works, what it does with your data, and why it's safe to use.",
            font=Fonts.BODY,
            text_color=Colors.TEXT_SECONDARY,
            wraplength=700,
            justify="left",
            anchor="w",
        ).pack(fill="x", anchor="w", pady=(0, Dimensions.SECTION_GAP))

        # ════════════════════════════════════════════════════════════
        #   SECTION 1: About the App
        # ════════════════════════════════════════════════════════════
        self._section_header(container, "💡", "About PowerPilot")

        about_questions = [
            (
                "⚡",
                "What does PowerPilot actually do?",
                "PowerPilot is a battery optimization tool for Windows. "
                "It monitors your battery health, tracks running processes, "
                "and lets you quickly disable non-essential background services "
                "that drain your battery. You can also apply 'Loadout Profiles' "
                "(like Work, Gaming, Battery Saver) that adjust your power plan, "
                "brightness, notifications, and more — all with a single click.",
                Colors.ACCENT,
            ),
            (
                "🔋",
                "How does the Battery Optimizer work?",
                "The Battery Optimizer scans all running processes on your system "
                "and categorizes them into three groups:\n\n"
                "• Windows & System — Built-in Windows background services\n"
                "• Microsoft Apps — Office, Teams, OneDrive, etc.\n"
                "• Third-Party Apps — Everything else\n\n"
                "Mandatory system processes (like explorer.exe, csrss.exe, and svchost.exe) "
                "are always protected and cannot be stopped. For everything else, you can "
                "stop processes individually or in bulk to free up memory and CPU, "
                "which directly extends your battery life.",
                Colors.SUCCESS,
            ),
            (
                "🧹",
                "What is 'Clean Sweep'?",
                "Clean Sweep is a one-click feature that terminates all user-started "
                "processes. It first tries a graceful shutdown, and if a process doesn't "
                "respond within 3 seconds, it force-kills it. System processes (like "
                "Windows services, explorer.exe, etc.) are always protected and won't "
                "be affected. This is useful when you want a quick cleanup before "
                "switching to battery power.",
                Colors.WARNING,
            ),
            (
                "🎯",
                "What are Loadout Profiles?",
                "Loadout Profiles are pre-configured system settings bundles. "
                "For example:\n\n"
                "• Work — Balanced power plan, notifications off, 70% brightness\n"
                "• Gaming — High performance, no interruptions, 100% brightness\n"
                "• Battery Saver — Power saver plan, low brightness, Bluetooth off\n"
                "• Idle — Minimal resources for when you step away\n\n"
                "You can activate any profile instantly and deactivate to return "
                "to your previous settings.",
                Colors.ACCENT,
            ),
            (
                "🪟",
                "Which Windows background processes can I safely stop?",
                "PowerPilot identifies and labels processes as either mandatory (🔒) "
                "or stoppable. Processes you can safely stop include:\n\n"
                "• Windows Search Indexer (searchindexer.exe)\n"
                "• Windows Widgets (widgets.exe, widgetservice.exe)\n"
                "• Compatibility Telemetry (compattelrunner.exe)\n"
                "• Game Bar services (gamebarpresencewriter.exe)\n"
                "• Phone Link / Your Phone (yourphone.exe)\n"
                "• Background Transfer Host\n\n"
                "Stopping these frees memory and CPU but won't crash your system. "
                "Some may restart automatically if Windows needs them.",
                Colors.SUCCESS,
            ),
        ]

        for icon, q, a, color in about_questions:
            FAQItem(container, icon, q, a, accent_color=color).pack(
                fill="x", pady=3
            )

        # ════════════════════════════════════════════════════════════
        #   SECTION 2: Privacy & Data
        # ════════════════════════════════════════════════════════════
        self._section_header(container, "🔒", "Privacy & Data Security")

        privacy_questions = [
            (
                "🛡️",
                "Does PowerPilot collect or send my data anywhere?",
                "Absolutely not. PowerPilot runs 100% locally on your machine. "
                "It does NOT:\n\n"
                "• Connect to the internet\n"
                "• Send any data to external servers\n"
                "• Upload process lists, battery info, or usage patterns\n"
                "• Phone home or check for analytics\n\n"
                "Everything stays on your computer. The only file PowerPilot creates "
                "is a local config.json in your AppData folder to remember your "
                "settings (like excluded processes and loadout preferences).",
                Colors.SUCCESS,
            ),
            (
                "📁",
                "What data does PowerPilot store on my computer?",
                "PowerPilot stores a single configuration file at:\n\n"
                "%APPDATA%\\PowerPilot\\config.json\n\n"
                "This file contains only your preferences:\n"
                "• Whether autorun is enabled\n"
                "• Your excluded processes list\n"
                "• Custom loadout profiles\n"
                "• UI preferences (start minimized, etc.)\n\n"
                "No personal data, no browsing history, no passwords, "
                "no screenshots — nothing sensitive is ever stored.",
                Colors.ACCENT,
            ),
            (
                "🔐",
                "Does PowerPilot log or record my process activity?",
                "No. PowerPilot reads your current process list in real-time "
                "using the 'psutil' library (the same library used by system "
                "monitoring tools). This data exists only in memory while the "
                "app is running and is never written to disk, logged, or saved. "
                "When you close PowerPilot, all process data is gone.",
                Colors.SUCCESS,
            ),
            (
                "🌐",
                "Does PowerPilot need internet access?",
                "No. PowerPilot works entirely offline. It has no network "
                "features, no update checker, no telemetry, and no cloud "
                "sync. It uses only local Windows APIs (psutil, powercfg, "
                "WMI, and the Windows Registry) to manage your system.",
                Colors.ACCENT,
            ),
            (
                "👁️",
                "Can PowerPilot see my passwords or personal files?",
                "No. PowerPilot only reads process metadata — names, PIDs, "
                "CPU usage, and memory usage. It cannot read:\n\n"
                "• File contents on your disk\n"
                "• Browser history or saved passwords\n"
                "• Email, chat messages, or documents\n"
                "• Keystrokes or clipboard content\n"
                "• Screenshots or webcam data\n\n"
                "It's purely a system resource monitor and optimizer.",
                Colors.SUCCESS,
            ),
            (
                "🗑️",
                "How do I completely uninstall PowerPilot?",
                "To remove PowerPilot entirely:\n\n"
                "1. Open Settings → Disable 'Start with Windows' toggle\n"
                "2. Close PowerPilot\n"
                "3. Delete the PowerPilot application folder\n"
                "4. (Optional) Delete %APPDATA%\\PowerPilot to remove saved settings\n\n"
                "That's it. PowerPilot doesn't install system drivers, "
                "kernel modules, or hidden services. The only registry key "
                "it creates is for autorun (HKCU\\Run), and disabling the "
                "toggle in step 1 removes that.",
                Colors.ACCENT,
            ),
        ]

        for icon, q, a, color in privacy_questions:
            FAQItem(container, icon, q, a, accent_color=color).pack(
                fill="x", pady=3
            )

        # ════════════════════════════════════════════════════════════
        #   SECTION 3: Safety & Troubleshooting
        # ════════════════════════════════════════════════════════════
        self._section_header(container, "⚙️", "Safety & Troubleshooting")

        safety_questions = [
            (
                "⚠️",
                "Can PowerPilot break my system?",
                "No. PowerPilot has extensive safety measures:\n\n"
                "• Critical processes (csrss.exe, lsass.exe, svchost.exe, dwm.exe, etc.) "
                "are hardcoded as mandatory and CANNOT be terminated\n"
                "• Processes running under SYSTEM, LOCAL SERVICE, or NETWORK SERVICE "
                "accounts are automatically protected\n"
                "• Explorer.exe (your desktop) is always protected\n"
                "• Confirmation dialogs are shown before any bulk operations\n\n"
                "Even if you stop a non-essential background service, Windows will "
                "often restart it automatically when needed.",
                Colors.WARNING,
            ),
            (
                "🔄",
                "What happens if I stop a process I need?",
                "If you accidentally stop a process you're using (like a browser "
                "or music player), simply relaunch it from your Start Menu or "
                "taskbar. No data is permanently lost — processes can always be "
                "restarted. For most Windows background services, they'll restart "
                "automatically on their own.\n\n"
                "You can also use the Process Exclusions list in Settings to "
                "permanently protect specific processes from being affected by "
                "Clean Sweep or the Battery Optimizer.",
                Colors.ACCENT,
            ),
            (
                "🔑",
                "Does PowerPilot need administrator privileges?",
                "For basic features (process monitoring, Clean Sweep, loadout profiles), "
                "no admin rights are needed. However, some advanced features may work "
                "better with admin privileges:\n\n"
                "• Stopping certain system services (Windows Search, etc.)\n"
                "• Changing power plans via powercfg\n"
                "• Pausing Windows Update\n"
                "• Adjusting display brightness via WMI\n\n"
                "PowerPilot will still work without admin rights — some operations "
                "may simply fail silently if they need elevated access.",
                Colors.WARNING,
            ),
            (
                "📊",
                "Why do some processes show 0% CPU?",
                "CPU usage is measured as a snapshot at the time of scanning. "
                "A process showing 0% CPU means it wasn't actively using the CPU "
                "at that exact moment — it may still be consuming memory or doing "
                "occasional background work. This is normal and doesn't mean the "
                "process isn't using resources.",
                Colors.ACCENT,
            ),
            (
                "💻",
                "What Windows versions does PowerPilot support?",
                "PowerPilot is designed for Windows 10 and Windows 11. It uses "
                "standard Windows APIs (powercfg, WMI, and the Registry) that "
                "are available on both versions. Some features like the Widgets "
                "detection are Windows 11-specific but won't cause errors on "
                "Windows 10 — they'll simply have fewer processes to manage.",
                Colors.SUCCESS,
            ),
        ]

        for icon, q, a, color in safety_questions:
            FAQItem(container, icon, q, a, accent_color=color).pack(
                fill="x", pady=3
            )

        # ── Bottom trust banner ─────────────────────────────────────
        trust_card = ctk.CTkFrame(
            container,
            fg_color=Colors.ACCENT_SUBTLE,
            corner_radius=Dimensions.CARD_CORNER_RADIUS,
            border_width=1,
            border_color=Colors.ACCENT_DARK,
        )
        trust_card.pack(fill="x", pady=(Dimensions.SECTION_GAP, 8))

        trust_inner = ctk.CTkFrame(trust_card, fg_color="transparent")
        trust_inner.pack(fill="x", padx=24, pady=20)

        ctk.CTkLabel(
            trust_inner,
            text="🛡️  Your Privacy is Our Priority",
            font=Fonts.HEADING_2,
            text_color=Colors.ACCENT,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            trust_inner,
            text="PowerPilot is a fully offline, open-source battery optimizer. "
                 "It never connects to the internet, never collects data, and never "
                 "shares your information with anyone. Your system, your control.",
            font=Fonts.BODY,
            text_color=Colors.TEXT_SECONDARY,
            wraplength=650,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(8, 0))

        # Trust badges
        badges_frame = ctk.CTkFrame(trust_inner, fg_color="transparent")
        badges_frame.pack(anchor="w", pady=(12, 0))

        badges = [
            ("🔒 Zero Data Collection", Colors.SUCCESS),
            ("📴 100% Offline", Colors.ACCENT),
            ("🗂️ Open Source", Colors.WARNING),
            ("🛡️ No Telemetry", Colors.SUCCESS),
        ]

        for badge_text, badge_color in badges:
            badge = ctk.CTkLabel(
                badges_frame,
                text=f"  {badge_text}  ",
                font=Fonts.CAPTION_BOLD,
                text_color=badge_color,
                fg_color=Colors.BG_CARD,
                corner_radius=6,
                padx=8,
                pady=4,
            )
            badge.pack(side="left", padx=(0, 6))

    def _section_header(self, parent, icon, title):
        """Create a section header with icon and title.

        Args:
            parent: Parent widget.
            icon: Emoji icon.
            title: Section title text.
        """
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", pady=(Dimensions.SECTION_GAP, 8))

        ctk.CTkLabel(
            header,
            text=icon,
            font=("Segoe UI Emoji", 16),
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text=f"  {title}",
            font=Fonts.HEADING_2,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        # Divider line
        ctk.CTkFrame(
            parent,
            fg_color=Colors.BORDER,
            height=1,
        ).pack(fill="x", pady=(0, 8))
