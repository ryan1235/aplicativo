import json
import os
import logging

class ArtilleryManager:
    """
    Manager for handling artillery weapons and calculating their stats.
    Loads configurations from arty.json.
    """
    def __init__(self, json_path: str = "data/arty.json"):
        self.weapons = []
        self.active_weapon = None
        self.json_path = json_path
        self.load_weapons()

    def load_weapons(self) -> None:
        """Loads weapon configurations from the arty.json file."""
        if not os.path.exists(self.json_path):
            logging.error(f"Artillery configuration file {self.json_path} not found.")
            return

        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.weapons = data.get("weapons", [])
            
            if self.weapons and self.active_weapon is None:
                self.active_weapon = self.weapons[0]
                
            logging.info(f"Loaded {len(self.weapons)} artillery weapons from {self.json_path}.")
        except Exception as e:
            logging.error(f"Failed to load artillery configuration: {e}")
            self.weapons = []

    def get_weapon_list(self) -> list[dict]:
        """Returns the list of all available weapons."""
        return self.weapons

    def get_weapon_names(self) -> list[str]:
        """Returns a list of weapon names for UI selection."""
        return [w.get("name", "Unknown") for w in self.weapons]

    def set_active_weapon_by_index(self, index: int) -> bool:
        """Sets the active weapon using its index in the list."""
        if 0 <= index < len(self.weapons):
            self.active_weapon = self.weapons[index]
            return True
        return False

    def get_active_weapon_info(self) -> dict:
        """Returns the currently active weapon's dictionary."""
        return self.active_weapon or {}
