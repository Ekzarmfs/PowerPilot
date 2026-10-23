"""
PowerPilot Design System & Theme Engine.
Precision-engineered telemetry theme for Windows 11.
Atmospheric Deep Obsidian Titanium surfaces with Electric Ion Cerulean accent,
optical variable typography, and high-clarity status diagnostics.
"""


# ── Color System ───────────────────────────────────────────────────
# Deep Obsidian Titanium elevation stack with Electric Ion signature

class Colors:
    """Centralized color definitions for PowerPilot.
    
    Adheres to Windows 11 Fluent 2 elevation hierarchy:
    Obsidian Base -> Carbon Dock -> Milled Titanium Card -> Elevated Popups.
    """

    # Backgrounds & Elevation Hierarchy
    BG_PRIMARY = "#090d16"        # Main application background (Deep Obsidian Horizon)
    BG_SECONDARY = "#0e1320"      # Sidebar & docking frame (Carbon Slate)
    BG_CARD = "#141a29"           # Standard surface cards & table rows (Milled Titanium)
    BG_CARD_HOVER = "#1b2337"     # Interactive row & card hover state
    BG_ELEVATED = "#222c44"       # Modals, flyouts, and pill containers
    BG_INPUT = "#0a0e17"          # Recessed inputs, search bars, and sensor cavities

    # Structural Boundaries & Micro-Strokes (1px Crisp Precision)
    BORDER = "#1f273d"            # Standard architectural boundary
    BORDER_LIGHT = "#2c3856"      # Subtle specular top-edge highlight
    BORDER_ACCENT = "#38bdf8"     # Focused / active state boundary

    # Signature Accent — Electric Ion Cerulean
    # Evoking pure electrical ionization, high-efficiency voltage, and flight telemetry.
    ACCENT = "#38bdf8"            # Primary brand accent (Electric Ion Sky)
    ACCENT_DARK = "#0284c7"       # Deep Ion Cobalt (buttons, progress fill)
    ACCENT_HOVER = "#60a5fa"      # Energized hover glow
    ACCENT_PRESSED = "#0369a1"    # Mechanical engagement state
    ACCENT_SUBTLE = "#0c2135"     # Ambient background glow for active controls
    ACCENT_GLOW = "#00f0ff"       # High-luminance charging arc

    # High-Legibility Typography Contrast Tiers
    TEXT_PRIMARY = "#f1f5f9"      # Cool Platinum White (primary headings, values)
    TEXT_SECONDARY = "#94a3b8"    # Slate Silver (labels, body descriptions, table subtext)
    TEXT_TERTIARY = "#526079"     # Muted Graphite (PIDs, inactive icons, disabled states)
    TEXT_ACCENT = "#38bdf8"       # Ion Cerulean callouts and live telemetry

    # Telemetry Status & Health Diagnostics
    SUCCESS = "#10b981"           # Emerald Current — healthy battery, optimal state
    SUCCESS_BG = "#062c1e"        # Deep emerald reservoir
    SUCCESS_HOVER = "#059669"     # Hover state for success actions
    WARNING = "#f59e0b"           # Solar Amber — moderate battery, caution
    WARNING_BG = "#2e1d08"        # Deep solar glow
    WARNING_HOVER = "#d97706"     # Hover state for warning actions
    DANGER = "#f43f5e"            # Crimson Pulse — critical low battery, kill actions
    DANGER_BG = "#330d17"         # Deep crimson reservoir
    DANGER_HOVER = "#e11d48"      # Hover state for destructive actions

    # Extended Categorization Accents
    PURPLE = "#a78bfa"            # Violet Ion — third-party background services
    PURPLE_BG = "#231b38"         # Subdued violet cavity

    # Dynamic Battery Gauge Arcs
    BATTERY_FULL = "#10b981"      # > 60% (Emerald Current)
    BATTERY_MID = "#f59e0b"       # 20-60% (Solar Amber)
    BATTERY_LOW = "#f43f5e"       # < 20% (Crimson Pulse)
    BATTERY_CHARGING = "#00f0ff"  # Plugged in (Pure Electric Arc)
    BATTERY_BG = "#182236"        # Deep aerospace gauge track

    # Sidebar Navigation System
    NAV_ACTIVE = "#162035"        # Selected tab surface
    NAV_HOVER = "#121827"         # Hovered tab surface
    NAV_INDICATOR = "#38bdf8"     # Precision vertical ion line

    # Relative Battery Drain Badge Tiers
    DRAIN_CRITICAL = "#f43f5e"    # >= 25% drain
    DRAIN_CRITICAL_BG = "#330d17"
    DRAIN_HIGH = "#f59e0b"        # >= 12% drain
    DRAIN_HIGH_BG = "#2e1d08"
    DRAIN_MODERATE = "#fbbf24"    # >= 4% drain
    DRAIN_MODERATE_BG = "#241a0b"
    DRAIN_LOW = "#94a3b8"         # < 4% drain
    DRAIN_LOW_BG = "#1b2337"


# ── Typography System ──────────────────────────────────────────────

class Fonts:
    """Font definitions — Windows 11 Variable Typography with Cascadia Numerals.
    
    Uses 'Segoe UI Variable Display' for optical hero scaling and headings,
    'Segoe UI Variable Text' for body, and 'Cascadia Code' for fixed-width
    tabular telemetry.
    """

    FAMILY_DISPLAY = "Segoe UI Variable Display"
    FAMILY_TEXT = "Segoe UI Variable Text"
    FAMILY = "Segoe UI"
    FAMILY_SEMIBOLD = "Segoe UI Semibold"
    FAMILY_MONO = "Cascadia Code"
    FAMILY_MONO_FALLBACK = "Consolas"
    FAMILY_EMOJI = "Segoe UI Emoji"

    # Font tuples: (family, size, weight)
    DISPLAY = (FAMILY_DISPLAY, 46, "bold")        # Dominant hero battery percentage
    DISPLAY_LIGHT = (FAMILY_DISPLAY, 40)          # Large telemetry stat values
    HEADING_1 = (FAMILY_DISPLAY, 20, "bold")      # Page and view titles
    HEADING_2 = (FAMILY_DISPLAY, 14, "bold")      # Section headers & collapsible bars
    HEADING_3 = (FAMILY_TEXT, 13, "bold")         # Card titles and dialogue titles
    BODY = (FAMILY_TEXT, 12)                      # Standard readable body text
    BODY_BOLD = (FAMILY_TEXT, 12, "bold")         # Emphasized body text
    BODY_SMALL = (FAMILY_TEXT, 11)                # Secondary descriptions and hints
    CAPTION = (FAMILY_TEXT, 10)                   # Captions, metadata, column headers
    CAPTION_BOLD = (FAMILY_TEXT, 10, "bold")      # Badges, chip labels, button micro-copy
    TINY = (FAMILY_TEXT, 9)                       # Sub-labels and version tags
    MONO = (FAMILY_MONO, 12)                      # Tabular telemetry & PIDs
    MONO_SMALL = (FAMILY_MONO, 10)                # Dense table telemetry
    MONO_BOLD = (FAMILY_MONO, 12, "bold")         # Highlighted % drain values
    NAV_LABEL = (FAMILY_TEXT, 11)                 # Sidebar navigation labels
    BUTTON = (FAMILY_TEXT, 12, "bold")            # Action button text
    ICON = (FAMILY_EMOJI, 18)                     # Emoji iconography
    ICON_LARGE = (FAMILY_EMOJI, 24)               # Hero icons
    ICON_NAV = (FAMILY_EMOJI, 16)                 # Sidebar navigation glyphs


# ── Dimensions & Layout Rhythms ────────────────────────────────────

class Dimensions:
    """Layout geometry, corner radii, and spacing constants."""

    # Window Constraints
    WINDOW_WIDTH = 1060
    WINDOW_HEIGHT = 700
    WINDOW_MIN_WIDTH = 900
    WINDOW_MIN_HEIGHT = 600

    # Navigation Rail
    SIDEBAR_WIDTH = 210

    # Card & Container Geometry
    CARD_CORNER_RADIUS = 10
    CARD_PADDING = 16
    CARD_BORDER_WIDTH = 1

    # Button Geometry
    BUTTON_CORNER_RADIUS = 8
    BUTTON_HEIGHT = 36
    BUTTON_PADDING = 12

    # Spacing Grid
    SECTION_GAP = 16
    ITEM_GAP = 8
    INNER_PAD = 14


# ── Color Calculation Utilities ────────────────────────────────────

def get_battery_color(percent, is_charging=False):
    """Get the appropriate color for a battery level.

    Args:
        percent: Battery percentage (0-100).
        is_charging: Whether the battery is currently charging.

    Returns:
        str: Hex color string.
    """
    if is_charging:
        return Colors.BATTERY_CHARGING
    if percent > 60:
        return Colors.BATTERY_FULL
    if percent > 20:
        return Colors.BATTERY_MID
    return Colors.BATTERY_LOW


def get_health_color(percent):
    """Get the appropriate color for battery health level.

    Args:
        percent: Health percentage (0-100).

    Returns:
        str: Hex color string.
    """
    if percent > 80:
        return Colors.SUCCESS
    if percent > 50:
        return Colors.WARNING
    return Colors.DANGER


def get_drain_color_tuple(pwr):
    """Get (text_color, bg_color) tuple for relative battery drain percentage.

    Args:
        pwr: Power drain percentage (0-100).

    Returns:
        tuple[str, str]: (text_color, bg_color)
    """
    if pwr >= 25.0:
        return Colors.DRAIN_CRITICAL, Colors.DRAIN_CRITICAL_BG
    if pwr >= 12.0:
        return Colors.DRAIN_HIGH, Colors.DRAIN_HIGH_BG
    if pwr >= 4.0:
        return Colors.DRAIN_MODERATE, Colors.DRAIN_MODERATE_BG
    return Colors.DRAIN_LOW, Colors.DRAIN_LOW_BG
