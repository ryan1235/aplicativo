from PySide6.QtCore import Qt, Property, Signal, Slot, QRectF, QPointF
from PySide6.QtQuick import QQuickItem, QSGNode, QSGGeometryNode, QSGGeometry, QSGTextureMaterial, QSGSimpleTextureNode, QSGTexture
from PySide6.QtGui import QImage, QColor
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

ICON_MAP = {
    5: "MapIconTownBaseTier1.webp",
    6: "MapIconTownBaseTier2.webp",
    7: "MapIconTownBaseTier3.webp",
    8: "MapIconTownBaseTier1.webp",
    9: "MapIconTownBaseTier2.webp",
    10: "MapIconTownBaseTier3.webp",
    11: "MapIconHospital.webp",
    12: "MapIconVehicle.webp",
    16: "MapIconManufacturing.webp",
    17: "MapIconManufacturing.webp",
    18: "Shipyard.webp",
    19: "MapIconTechCenter.webp",
    20: "MapIconSalvageColor.webp",
    21: "MapIconComponentsColor.webp",
    22: "MapIconFuel.webp",
    23: "MapIconSulfurColor.webp",
    27: "MapIconsKeep.webp",
    28: "MapIconObservationTower.webp",
    29: "MapIconRelicBase.webp",
    31: "MapIconSulfurMineColor.webp",
    32: "MapIconSulfurMineColor.webp",
    33: "MapIconStorageFacility.webp",
    34: "MapIconFactory.webp",
    35: "MapIconSafehouse.webp",
    36: "MapIconFactory.webp",
    37: "MapIconRocketSite.webp",
    38: "MapIconSalvageMineColor.webp",
    39: "MapIconConstructionYard.webp",
    40: "MapIconComponentMineColor.webp",
    41: "MapIconFacilityMineOilRig.webp",
    42: "MapIconRocketTarget.webp",
    43: "MapIconMortarHouse.webp",
    45: "MapIconRelicBase.webp",
    46: "MapIconRelicBase.webp",
    47: "MapIconRelicBase.webp",
    48: "MapIconStormcannon.webp",
    49: "MapIconIntelcenter.webp",
    50: "MapIconBorderBase.webp",
    51: "MapIconMassProductionFactory.webp",
    52: "MapIconSeaport.webp",
    53: "MapIconCoastalGun.webp",
    54: "MapIconFactory.webp",
    55: "MapIconBorderBase.webp",
    56: "MapIconTownBaseTier1.webp",
    57: "MapIconTownBaseTier2.webp",
    58: "MapIconTownBaseTier3.webp",
    59: "MapIconStormcannon.webp",
    60: "MapIconIntelcenter.webp",
    61: "MapIconCoalFieldColor.webp",
    62: "MapIconOilFieldColor.webp",
    70: "MapIconRocketTarget.webp",
    71: "MapIconRocketGroundZero.webp",
    84: "MapIconMaintenanceTunnel.webp",
    85: "MapIconTrainBridge.webp",
    86: "Shipyard.webp",
    87: "MapIconFacilityMineOilRig.webp",
    88: "MapIconAircraftDeposit.webp"
}

class MapIconsRenderer(QQuickItem):
    itemsChanged = Signal()
    mapStateChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFlag(QQuickItem.ItemHasContents, True)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setAcceptHoverEvents(True)
        print("MapIconsRenderer instantiated!")

        self._items = []
        self._mapScale = 1.0
        self._mapOffsetX = 0.0
        self._mapOffsetY = 0.0
        self._currentZoom = 2
        self._centerX = 0.0
        self._centerY = 0.0

        self._showResources = False
        self._showIcons = False
        self._showStockFilter = True
        self._showMainStructures = True

        self._textures = {}

    def get_texture(self, type_id, team_id):
        key = f"{type_id}_{team_id}"
        if key in self._textures:
            return self._textures[key]

        filename = ICON_MAP.get(int(type_id), "unknown.webp")
        path = BASE_DIR / "img" / "iconmap" / filename
        if not path.exists():
            return None

        img = QImage(str(path))
        if team_id == 1:
            img = self.apply_colorization(img, QColor("#3b82f6"))
        elif team_id == 2:
            img = self.apply_colorization(img, QColor("#22c55e"))

        texture = self.window().createTextureFromImage(img)
        self._textures[key] = texture
        return texture

    def apply_colorization(self, img, color):
        res = img.copy()
        res.convertTo(QImage.Format_ARGB32)
        for y in range(res.height()):
            for x in range(res.width()):
                p = res.pixelColor(x, y)
                if p.alpha() > 0:
                    r = int((p.red() * 0.2 + color.red() * 0.8))
                    g = int((p.green() * 0.2 + color.green() * 0.8))
                    b = int((p.blue() * 0.2 + color.blue() * 0.8))
                    res.setPixelColor(x, y, QColor(r, g, b, p.alpha()))
        return res

    @Property('QVariant', notify=itemsChanged)
    def itemsData(self):
        return self._items

    @itemsData.setter
    def itemsData(self, val):
        if hasattr(val, 'toVariant'):
            val = val.toVariant()
        self._items = val if isinstance(val, list) else list(val) if val else []
        print(f"MapIconsRenderer itemsData set! length={len(self._items)}")
        self.update()

    # --- Map Viewport Properties ---
    @Property(float, notify=mapStateChanged)
    def mapScale(self): return self._mapScale
    @mapScale.setter
    def mapScale(self, val): self._mapScale = val; self.update()

    @Property(float, notify=mapStateChanged)
    def mapOffsetX(self): return self._mapOffsetX
    @mapOffsetX.setter
    def mapOffsetX(self, val): self._mapOffsetX = val; self.update()

    @Property(float, notify=mapStateChanged)
    def mapOffsetY(self): return self._mapOffsetY
    @mapOffsetY.setter
    def mapOffsetY(self, val): self._mapOffsetY = val; self.update()

    @Property(int, notify=mapStateChanged)
    def currentZoom(self): return self._currentZoom
    @currentZoom.setter
    def currentZoom(self, val): self._currentZoom = val; self.update()

    @Property(float, notify=mapStateChanged)
    def centerX(self): return self._centerX
    @centerX.setter
    def centerX(self, val): self._centerX = val; self.update()

    @Property(float, notify=mapStateChanged)
    def centerY(self): return self._centerY
    @centerY.setter
    def centerY(self, val): self._centerY = val; self.update()

    # --- Filters ---
    @Property(bool, notify=mapStateChanged)
    def showResources(self): return self._showResources
    @showResources.setter
    def showResources(self, val): self._showResources = val; self.update()

    @Property(bool, notify=mapStateChanged)
    def showIcons(self): return self._showIcons
    @showIcons.setter
    def showIcons(self, val): self._showIcons = val; self.update()

    @Property(bool, notify=mapStateChanged)
    def showStockFilter(self): return self._showStockFilter
    @showStockFilter.setter
    def showStockFilter(self, val): self._showStockFilter = val; self.update()

    @Property(bool, notify=mapStateChanged)
    def showMainStructures(self): return self._showMainStructures
    @showMainStructures.setter
    def showMainStructures(self, val): self._showMainStructures = val; self.update()

    itemHovered = Signal(str, str, bool, float, float)
    itemClicked = Signal(str)

    def hoverMoveEvent(self, event):
        pos = event.position()
        found = self._find_item_at(pos.x(), pos.y())
        if found:
            hasStock = found.get("stock") is not None
            self.itemHovered.emit(found.get("name", ""), str(found.get("type", "")), hasStock, pos.x(), pos.y())
        else:
            self.itemHovered.emit("", "", False, 0, 0)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        pos = event.position()
        found = self._find_item_at(pos.x(), pos.y())
        if found:
            self.itemClicked.emit(found.get("name", ""))
        super().mousePressEvent(event)

    def _is_resource(self, t):
        return t in (20, 21, 22, 23, 32, 38, 40, 61, 62)

    def _is_main_structure(self, t):
        return t in (5, 6, 7, 8, 9, 10, 56, 57, 58, 29, 45, 46, 47, 52, 33, 35, 27, 50, 55, 88)

    def _should_show(self, item, inBounds):
        if not inBounds:
            return False
        hasStock = self._showStockFilter and item.get("stock") is not None
        if hasStock:
            return True
        if self._currentZoom < 5:
            return False
        
        t = int(item.get("type", 0))
        if self._is_main_structure(t):
            return self._showMainStructures
        if self._is_resource(t):
            return self._showResources
        return self._showIcons

    def _find_item_at(self, sx, sy):
        zoomFactor = 2 ** self._currentZoom
        
        for item in self._items:
            x_api = item.get("x", 0)
            y_api = item.get("y", 0)
            
            worldPxX = ((x_api * self._mapScale) + self._mapOffsetX) * zoomFactor
            worldPxY = ((-y_api * self._mapScale) + self._mapOffsetY) * zoomFactor
            
            screenX = worldPxX
            screenY = worldPxY
            
            if self._should_show(item, True):
                # Check bounding box
                icon_size = 30 if item.get("stock") is not None else 24
                if (screenX - icon_size/2 <= sx <= screenX + icon_size/2) and \
                   (screenY - icon_size/2 <= sy <= screenY + icon_size/2):
                    return item
        return None

    def updatePaintNode(self, oldNode, updatePaintNodeData):
        if not oldNode:
            oldNode = QSGNode()

        if not self._items or self.width() <= 0 or self.height() <= 0:
            while oldNode.childCount() > 0:
                child = oldNode.firstChild()
                oldNode.removeChildNode(child)
            if hasattr(self, '_nodes'):
                self._nodes.clear()
            return oldNode

        if not hasattr(self, '_nodes'):
            self._nodes = []

        zoomFactor = 2 ** self._currentZoom
        
        node_idx = 0

        for item in self._items:
            if not self._should_show(item, True):
                continue

            texture = self.get_texture(item.get("type", 0), item.get("team", 0))
            if not texture:
                continue

            x_api = item.get("x", 0)
            y_api = item.get("y", 0)
            
            worldPxX = ((x_api * self._mapScale) + self._mapOffsetX) * zoomFactor
            worldPxY = ((-y_api * self._mapScale) + self._mapOffsetY) * zoomFactor
            
            screenX = worldPxX
            screenY = worldPxY
            
            hasStock = self._showStockFilter and item.get("stock") is not None
            icon_size = 30 if hasStock else 24

            if node_idx < len(self._nodes):
                node = self._nodes[node_idx]
            else:
                node = QSGSimpleTextureNode()
                node.setFiltering(QSGTexture.Linear)
                self._nodes.append(node)
                oldNode.appendChildNode(node)

            node.setTexture(texture)
            node.setRect(screenX - icon_size/2, screenY - icon_size/2, icon_size, icon_size)
            node_idx += 1

        # Remove extra nodes
        while len(self._nodes) > node_idx:
            node = self._nodes.pop()
            oldNode.removeChildNode(node)

        return oldNode
