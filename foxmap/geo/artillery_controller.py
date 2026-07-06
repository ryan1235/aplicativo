import os
from PySide6.QtCore import QObject, Property, Signal, Slot
from .artillery_manager import ArtilleryManager
from .artillery_renderer import ArtilleryRenderer

class ArtilleryController(QObject):
    """
    QObject controller that exposes Artillery functionality to QML.
    """
    weaponChanged = Signal()
    configChanged = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        json_path = os.path.join(base_dir, "data", "arty.json")
        self.manager = ArtilleryManager(json_path)
        self.renderer = ArtilleryRenderer()
        
        self._show_range = True
        self._show_dispersion = True
        self._show_line = True
        self._show_distances = True

    @Property(list, notify=weaponChanged)
    def weaponsList(self) -> list:
        return self.manager.get_weapon_names()

    @Property(int, notify=weaponChanged)
    def activeWeaponIndex(self) -> int:
        if self.manager.active_weapon:
            try:
                return self.manager.weapons.index(self.manager.active_weapon)
            except ValueError:
                pass
        return -1

    @activeWeaponIndex.setter
    def activeWeaponIndex(self, index: int) -> None:
        if self.manager.set_active_weapon_by_index(index):
            self.weaponChanged.emit()

    @Property('QVariant', notify=weaponChanged)
    def weaponInfo(self) -> dict:
        return self.manager.get_active_weapon_info()

    # --- UI Config Properties ---
    
    @Property(bool, notify=configChanged)
    def showRange(self) -> bool:
        return self._show_range
    
    @showRange.setter
    def showRange(self, val: bool) -> None:
        if self._show_range != val:
            self._show_range = val
            self.configChanged.emit()

    @Property(bool, notify=configChanged)
    def showDispersion(self) -> bool:
        return self._show_dispersion
    
    @showDispersion.setter
    def showDispersion(self, val: bool) -> None:
        if self._show_dispersion != val:
            self._show_dispersion = val
            self.configChanged.emit()

    @Property(bool, notify=configChanged)
    def showLine(self) -> bool:
        return self._show_line
    
    @showLine.setter
    def showLine(self, val: bool) -> None:
        if self._show_line != val:
            self._show_line = val
            self.configChanged.emit()

    @Property(bool, notify=configChanged)
    def showDistances(self) -> bool:
        return self._show_distances
    
    @showDistances.setter
    def showDistances(self, val: bool) -> None:
        if self._show_distances != val:
            self._show_distances = val
            self.configChanged.emit()

    @Slot(float, result='QVariant')
    def getOverlayData(self, distance_meters: float) -> dict:
        """
        Returns the radii in World Units for the current weapon at the given distance.
        """
        return self.renderer.get_overlay_data(self.manager.active_weapon, distance_meters)
