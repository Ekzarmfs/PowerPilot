"""
Loadout profile engine for PowerPilot.
Manages preset and custom usage profiles that adjust system settings in bulk.
"""

from core.power_manager import PowerManager
from core.notifications import NotificationManager


class Loadout:
    """Represents a single loadout profile with system settings."""

    def __init__(self, name, icon, description, settings=None):
        """
        Args:
            name: Display name of the loadout.
            icon: Emoji icon for the loadout.
            description: Human-readable description.
            settings: Dict of system settings to apply.
        """
        self.name = name
        self.icon = icon
        self.description = description
        self.settings = settings or {}

    def to_dict(self):
        """Serialize loadout to a dict for config storage."""
        return {
            "name": self.name,
            "icon": self.icon,
            "description": self.description,
            "settings": self.settings,
        }

    @staticmethod
    def from_dict(data):
        """Deserialize a loadout from a dict."""
        return Loadout(
            name=data["name"],
            icon=data.get("icon", "⚙"),
            description=data.get("description", ""),
            settings=data.get("settings", {}),
        )


class LoadoutManager:
    """Manages loadout profiles and orchestrates their application."""

    DEFAULT_LOADOUTS = {
        "work": Loadout(
            name="Work",
            icon="💼",
            description="Focus mode for uninterrupted productivity. Blocks incoming Windows notifications, pauses background search indexing, sets balanced power, and tunes display brightness to 70%.",
            settings={
                "notifications": False,
                "power_plan": "balanced",
                "kill_background": False,
                "search_indexing": False,
                "brightness": 70,
            },
        ),
        "gaming": Loadout(
            name="Gaming",
            icon="🎮",
            description="Maximum throughput and FPS stability. Blocks toast popups and distractions, pauses disk search indexing, and unleashes High Performance power with 100% brightness.",
            settings={
                "notifications": False,
                "power_plan": "high_performance",
                "kill_background": False,
                "search_indexing": False,
                "brightness": 100,
            },
        ),
        "battery_saver": Loadout(
            name="Battery Saver",
            icon="🔋",
            description="Maximum battery endurance on the go. Shuts down Bluetooth wireless radios, pauses background indexing, engages aggressive Power Saver CPU throttling, and dims display to 30%.",
            settings={
                "notifications": True,
                "power_plan": "power_saver",
                "kill_background": False,
                "search_indexing": False,
                "brightness": 30,
                "bluetooth": False,
            },
        ),
        "idle": Loadout(
            name="Idle",
            icon="😴",
            description="Deep conservation mode for stepping away. Blocks all notifications, turns off Bluetooth radios, pauses disk indexing, and dims screen to 10% on Power Saver.",
            settings={
                "notifications": False,
                "power_plan": "power_saver",
                "kill_background": False,
                "search_indexing": False,
                "brightness": 10,
                "bluetooth": False,
            },
        ),
    }

    def __init__(self, power_manager=None, notification_manager=None, process_tracker=None):
        """
        Args:
            power_manager: PowerManager instance (created if not provided).
            notification_manager: NotificationManager instance.
            process_tracker: ProcessTracker instance for kill_background.
        """
        self.power_manager = power_manager or PowerManager()
        self.notification_manager = notification_manager or NotificationManager()
        self.process_tracker = process_tracker
        self.active_loadout = None
        self.loadouts = dict(self.DEFAULT_LOADOUTS)
        self.custom_loadouts = {}

    def get_loadout(self, key):
        """Get a loadout by key name.

        Args:
            key: Loadout key (e.g. 'work', 'gaming').

        Returns:
            Loadout or None.
        """
        return self.loadouts.get(key) or self.custom_loadouts.get(key)

    def get_all_loadouts(self):
        """Get all loadouts (default + custom).

        Returns:
            dict: Mapping of key -> Loadout.
        """
        all_loadouts = {}
        all_loadouts.update(self.loadouts)
        all_loadouts.update(self.custom_loadouts)
        return all_loadouts

    def add_custom_loadout(self, key, loadout):
        """Add a custom loadout profile.

        Args:
            key: Unique key for the loadout.
            loadout: Loadout instance.
        """
        self.custom_loadouts[key] = loadout

    def remove_custom_loadout(self, key):
        """Remove a custom loadout by key."""
        self.custom_loadouts.pop(key, None)
        if self.active_loadout == key:
            self.active_loadout = None

    def apply_loadout(self, key):
        """Apply a loadout profile, changing system settings.

        Args:
            key: Loadout key to apply.

        Returns:
            dict: Results of each setting change, or False if loadout not found.
        """
        loadout = self.get_loadout(key)
        if not loadout:
            return False

        settings = loadout.settings
        results = {}

        # Power plan
        if "power_plan" in settings:
            results["power_plan"] = self.power_manager.set_plan(settings["power_plan"])

        # Notifications
        if "notifications" in settings:
            if settings["notifications"]:
                results["notifications"] = (
                    self.notification_manager.enable_notifications()
                )
            else:
                results["notifications"] = (
                    self.notification_manager.disable_notifications()
                )

        # Brightness
        if "brightness" in settings:
            results["brightness"] = self.power_manager.set_brightness(
                settings["brightness"]
            )

        # Search indexing
        if "search_indexing" in settings:
            if settings["search_indexing"]:
                results["search_indexing"] = (
                    self.notification_manager.enable_search_indexing()
                )
            else:
                results["search_indexing"] = (
                    self.notification_manager.disable_search_indexing()
                )

        # Bluetooth
        if "bluetooth" in settings:
            results["bluetooth"] = self.notification_manager.set_bluetooth(
                settings["bluetooth"]
            )

        # Kill background processes (only if explicitly enabled)
        if settings.get("kill_background") and self.process_tracker:
            killed = self.process_tracker.clean_sweep()
            results["kill_background"] = killed

        self.active_loadout = key
        return results

    def deactivate(self):
        """Deactivate the current loadout and restore default system settings."""
        self.notification_manager.enable_notifications()
        self.notification_manager.enable_search_indexing()
        self.power_manager.set_plan("balanced")
        self.active_loadout = None

    def get_active_loadout_key(self):
        """Get the key of the currently active loadout, or None."""
        return self.active_loadout

    def export_custom_loadouts(self):
        """Export custom loadouts as a serializable dict for config storage."""
        return {
            key: loadout.to_dict()
            for key, loadout in self.custom_loadouts.items()
        }

    def import_custom_loadouts(self, data):
        """Import custom loadouts from config data.

        Args:
            data: Dict of key -> loadout dict.
        """
        for key, loadout_data in data.items():
            self.custom_loadouts[key] = Loadout.from_dict(loadout_data)
