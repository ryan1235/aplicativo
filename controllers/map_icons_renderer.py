from PySide6.QtCore import Qt, Property, Signal, Slot, QRectF, QPointF, QTimer
from PySide6.QtQuick import QQuickItem, QSGNode, QSGGeometryNode, QSGGeometry, QSGTextureMaterial, QSGSimpleTextureNode, QSGTexture
from PySide6.QtGui import QImage, QColor, QPainter
import os
from pathlib import Path

from .map_spatial_grid import MapSpatialGrid

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
        self._mapZoomScaleX = 4.0
        self._mapZoomScaleY = 4.0

        self._showResources = False
        self._showIcons = False
        self._showStockFilter = True
        self._showMainStructures = True

        self._spatial_grid = MapSpatialGrid(cell_size=1024)
        self._spatial_grid_dirty = True
        self._textures = {}
        self._texture_usage = {}  # track frame when each texture was last used
        self._max_cached_textures = 64  # limit cache to reduce memory
        self._frame_count = 0
        # Debounce updates to avoid frequent repaints during map interactions
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(16)  # ~60 FPS coalescing
        self._update_timer.timeout.connect(self.update)

    def get_texture(self, type_id, team_id):
        key = f"{type_id}_{team_id}"
        if key in self._textures:
            self._texture_usage[key] = self._frame_count  # mark as used
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
        self._texture_usage[key] = self._frame_count  # mark as used
        
        # Evict least-recently-used texture if cache exceeds max
        if len(self._textures) > self._max_cached_textures:
            lru_key = min(self._texture_usage.keys(), key=lambda k: self._texture_usage[k])
            del self._textures[lru_key]
            del self._texture_usage[lru_key]
        
        return texture

    def apply_colorization(self, img, color):
        res = img.copy()
        res = res.convertToFormat(QImage.Format_ARGB32_Premultiplied)
        painter = QPainter(res)
        
        # Multiply colors
        painter.setCompositionMode(QPainter.CompositionMode_Multiply)
        painter.fillRect(res.rect(), color)
        
        # Restore alpha mask from original image
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.drawImage(0, 0, img)
        painter.end()
        return res

    @Property('QVariant', notify=itemsChanged)
    def itemsData(self):
        return self._items

    @itemsData.setter
    def itemsData(self, val):
        if hasattr(val, 'toVariant'):
            val = val.toVariant()
        new_items = val if isinstance(val, list) else list(val) if val else []
        
        # Fast diff to avoid massive rebuilds when API returns same data
        if getattr(self, '_last_items_hash', None) is not None:
            import hashlib
            import json
            # Create a quick hash of the new items by their IDs and flags to detect changes
            try:
                # Assuming items are dicts with 'id', 'team', 'type', 'flags', 'stock'
                # Just stringifying the list of dicts is fast enough for 5000 items (takes ~2ms in Python)
                current_hash = hashlib.md5(json.dumps(new_items, sort_keys=True).encode('utf-8')).hexdigest()
                if current_hash == self._last_items_hash:
                    # No changes detected!
                    return
                self._last_items_hash = current_hash
            except Exception:
                pass
        else:
            try:
                import hashlib
                import json
                self._last_items_hash = hashlib.md5(json.dumps(new_items, sort_keys=True).encode('utf-8')).hexdigest()
            except Exception:
                pass

        self._items = new_items
        
        # Pre-compute spatial and rendering values for extreme performance during panning/zooming
        for item in self._items:
            # Pre-compute coordinates
            wx, wy = self._map_pixel(item)
            item['_wx'] = wx
            item['_wy'] = wy
            
            # Pre-compute fast filter flags
            t = int(item.get("type", 0))
            item['_is_resource'] = self._is_resource(t)
            item['_is_main_structure'] = self._is_main_structure(t)
            item['_has_stock'] = item.get("stock") is not None
            item['_icon_size'] = 30 if item['_has_stock'] else 24
            
        self._spatial_grid_dirty = True
        print(f"MapIconsRenderer itemsData set! length={len(self._items)}")
        self.schedule_update()

    # --- Map Viewport Properties ---
    @Property(float, notify=mapStateChanged)
    def mapScale(self): return self._mapScale
    @mapScale.setter
    def mapScale(self, val): self._mapScale = val; self._spatial_grid_dirty = True; self.schedule_update()

    @Property(float, notify=mapStateChanged)
    def mapOffsetX(self): return self._mapOffsetX
    @mapOffsetX.setter
    def mapOffsetX(self, val): self._mapOffsetX = val; self._spatial_grid_dirty = True; self.schedule_update()

    @Property(float, notify=mapStateChanged)
    def mapOffsetY(self): return self._mapOffsetY
    @mapOffsetY.setter
    def mapOffsetY(self, val): self._mapOffsetY = val; self._spatial_grid_dirty = True; self.schedule_update()

    @Property(int, notify=mapStateChanged)
    def currentZoom(self): return self._currentZoom
    @currentZoom.setter
    def currentZoom(self, val): self._currentZoom = val; self._spatial_grid_dirty = True; self.schedule_update()

    @Property(float, notify=mapStateChanged)
    def centerX(self): return self._centerX
    @centerX.setter
    def centerX(self, val): 
        self._centerX = val
        # Do not schedule_update() because MapIconsRenderer is inside overlayManager
        # and moves automatically via QML!

    @Property(float, notify=mapStateChanged)
    def centerY(self): return self._centerY
    @centerY.setter
    def centerY(self, val): 
        self._centerY = val
        # Do not schedule_update() because MapIconsRenderer is inside overlayManager

    @Property(float, notify=mapStateChanged)
    def mapZoomScaleX(self): return self._mapZoomScaleX
    @mapZoomScaleX.setter
    def mapZoomScaleX(self, val): self._mapZoomScaleX = val; self._spatial_grid_dirty = True; self.schedule_update()

    @Property(float, notify=mapStateChanged)
    def mapZoomScaleY(self): return self._mapZoomScaleY
    @mapZoomScaleY.setter
    def mapZoomScaleY(self, val): self._mapZoomScaleY = val; self._spatial_grid_dirty = True; self.schedule_update()

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
    def showMainStructures(self, val): self._showMainStructures = val; self.schedule_update()

    def schedule_update(self):
        self.update()

    itemHovered = Signal('QVariant', float, float)
    itemClicked = Signal('QVariant')

    def get_stock_bg_texture(self):
        if not hasattr(self, '_stock_bg'):
            from PySide6.QtGui import QPainter, QBrush, QPen, QPolygonF
            from PySide6.QtCore import QPointF
            import math
            img = QImage(44, 44, QImage.Format_ARGB32)
            img.fill(Qt.transparent)
            painter = QPainter(img)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QBrush(QColor(255, 215, 0, 150))) # Golden star (more opaque)
            painter.setPen(QPen(QColor(255, 215, 0, 255), 2))
            
            points = []
            cx, cy = 22, 24 # Shifted cy down by 2 to visually center the star
            outer_radius = 20
            inner_radius = 10
            for i in range(10):
                angle = i * math.pi / 5 - math.pi / 2
                radius = outer_radius if i % 2 == 0 else inner_radius
                points.append(QPointF(cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
                
            painter.drawPolygon(QPolygonF(points))
            painter.end()
            self._stock_bg = self.window().createTextureFromImage(img)
        return self._stock_bg

    def hoverMoveEvent(self, event):
        pos = event.position()
        found = self._find_item_at(pos.x(), pos.y())
        if found:
            self.itemHovered.emit(found, pos.x(), pos.y())
        else:
            self.itemHovered.emit(None, 0, 0)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        pos = event.position()
        found = self._find_item_at(pos.x(), pos.y())
        if found:
            self.itemClicked.emit(found)
        super().mousePressEvent(event)

    def _is_resource(self, t):
        return t in (20, 21, 22, 23, 32, 38, 40, 61, 62)

    def _is_main_structure(self, t):
        return t in (5, 6, 7, 8, 9, 10, 56, 57, 58, 29, 45, 46, 47, 52, 33, 35, 27, 50, 55, 88)

    def _should_show(self, item, inBounds):
        if not inBounds:
            return False
        
        # Extremely fast path using pre-computed flags
        if '_has_stock' in item:
            if item['_has_stock'] and self._showStockFilter: return True
            if self._currentZoom < 5: return False
            if item['_is_main_structure']: return self._showMainStructures
            if item['_is_resource']: return self._showResources
            return self._showIcons

        # Fallback for dynamic items
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

    def _map_pixel(self, item):
        # 0. Extremely fast path using pre-computed values
        if "_wx" in item:
            return item["_wx"], item["_wy"]

        # 1. Explicit world coordinates
        if "worldX" in item and "worldY" in item:
            return float(item["worldX"]), float(item["worldY"])
        if "world_x" in item and "world_y" in item:
            return float(item["world_x"]), float(item["world_y"])
            
        x_api = float(item.get("x", 0))
        y_api = float(item.get("y", 0))

        # 2. Region-based coordinates
        if "regionOffsetX" in item and "regionWidth" in item:
            wx = float(item["regionOffsetX"]) + (x_api * float(item["regionWidth"]))
            if "regionOffsetY" in item and "regionHeight" in item:
                wy = float(item["regionOffsetY"]) + (y_api * float(item["regionHeight"]))
            else:
                wy = (-y_api * self._mapScale) + self._mapOffsetY
            return wx, wy
            
        # 3. Normalized API coordinates with map dimensions
        if "mapWidth" in item and "mapHeight" in item:
            wx = x_api * float(item["mapWidth"])
            wy = abs(y_api) * float(item["mapHeight"])
            return wx, wy

        # 4. Fallback generic conversion
        wx = x_api * 80.0
        wy = -y_api * 80.0 - 4024.0
        return wx, wy

    def _rebuild_spatial_grid(self):
        if not self._spatial_grid_dirty:
            return
        self._spatial_grid.build(
            self._items,
            map_scale=self._mapScale,
            map_offset_x=self._mapOffsetX,
            map_offset_y=self._mapOffsetY,
        )
        self._spatial_grid_dirty = False

    def _find_item_at(self, sx, sy):
        self._rebuild_spatial_grid()
        # compute view bounds once to cull offscreen items
        w = self.width() if hasattr(self, 'width') else 0
        h = self.height() if hasattr(self, 'height') else 0
        margin = 48
        left = -margin
        right = w + margin
        top = -margin
        bottom = h + margin

        # Determine world bounds for culling based on screen bounds
        zoomFactor = 2 ** (self._currentZoom - 6)
        world_left = left / zoomFactor
        world_right = right / zoomFactor
        world_top = top / zoomFactor
        world_bottom = bottom / zoomFactor

        for item in self._spatial_grid.get_items_in_viewport(world_left, world_top, world_right, world_bottom):
            worldPxX, worldPxY = self._map_pixel(item)
            
            # MapIconsRenderer is inside overlayManager, which means its coordinate system
            # is already relative to the scaled map's top-left corner (0,0).
            # Therefore, we just apply the zoom scale.
            screenX = worldPxX * zoomFactor
            screenY = worldPxY * zoomFactor
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
            self._nodes = []
            self._textures = {}
            if hasattr(self, '_stock_bg'):
                del self._stock_bg

        if not self._items or self.width() <= 0 or self.height() <= 0:
            while oldNode.childCount() > 0:
                child = oldNode.firstChild()
                oldNode.removeChildNode(child)
            if hasattr(self, '_nodes'):
                self._nodes.clear()
            return oldNode

        if not hasattr(self, '_nodes'):
            self._nodes = []

        self._rebuild_spatial_grid()
        node_idx = 0

        # Compute view bounds once to cull offscreen items
        w = self.width()
        h = self.height()
        margin = 64
        left = -margin
        right = w + margin
        top = -margin
        bottom = h + margin

        zoomFactor = 2 ** (self._currentZoom - 6)
        world_left = left / zoomFactor
        world_right = right / zoomFactor
        world_top = top / zoomFactor
        world_bottom = bottom / zoomFactor

        for item in self._spatial_grid.get_items_in_viewport(world_left, world_top, world_right, world_bottom):
            if not self._should_show(item, True):
                continue

            texture = self.get_texture(item.get("type", 0), item.get("team", 0))
            if not texture:
                continue

            # Apply zoom to get position within overlayManager
            # Fast path for pre-computed coordinates
            if "_wx" in item:
                screenX = item["_wx"] * zoomFactor
                screenY = item["_wy"] * zoomFactor
                hasStock = item["_has_stock"] and self._showStockFilter
                icon_size = 44 if hasStock else 24
            else:
                worldPxX, worldPxY = self._map_pixel(item)
                screenX = worldPxX * zoomFactor
                screenY = worldPxY * zoomFactor
                hasStock = self._showStockFilter and item.get("stock") is not None
                icon_size = 44 if hasStock else 24

            if hasStock:
                if node_idx < len(self._nodes):
                    bg_node = self._nodes[node_idx]
                else:
                    bg_node = QSGSimpleTextureNode()
                    bg_node.setFiltering(QSGTexture.Linear)
                    self._nodes.append(bg_node)
                    oldNode.appendChildNode(bg_node)
                
                bg_node.setTexture(self.get_stock_bg_texture())
                bg_node.setRect(screenX - icon_size/2, screenY - icon_size/2, icon_size, icon_size)
                node_idx += 1

            if node_idx < len(self._nodes):
                node = self._nodes[node_idx]
            else:
                node = QSGSimpleTextureNode()
                node.setFiltering(QSGTexture.Linear)
                self._nodes.append(node)
                oldNode.appendChildNode(node)

            node.setTexture(texture)
            # Center the icon slightly smaller inside the background if hasStock
            fg_size = 24 if hasStock else icon_size
            node.setRect(screenX - fg_size/2, screenY - fg_size/2, fg_size, fg_size)
            node_idx += 1

        # Remove extra nodes
        while len(self._nodes) > node_idx:
            node = self._nodes.pop()
            oldNode.removeChildNode(node)

        # Increment frame counter for LRU eviction logic
        self._frame_count += 1

        return oldNode
