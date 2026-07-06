import math
from PySide6.QtQuick import QQuickPaintedItem
from PySide6.QtCore import Property, Slot, Signal, Qt, QRectF
from PySide6.QtGui import QPainter, QFont, QPen, QColor, QFontMetrics

class MapTextRenderer(QQuickPaintedItem):
    """
    A high-performance C++ backend renderer for map text labels (Hex names, Towns, etc.).
    It dynamically draws only the texts visible in the current viewport using QPainter.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items_data = []
        self._map_scale = 1.0
        self._map_offset_x = 0.0
        self._map_offset_y = 0.0
        self._current_zoom = 0.0
        self._center_x = 0.0
        self._center_y = 0.0
        self._show_hex_names = True
        self._show_major_cities = True
        self._show_minor_cities = True
        
        self.setAntialiasing(True)
        self.setOpaquePainting(False) # Allows background to show through
        self.setRenderTarget(QQuickPaintedItem.FramebufferObject)

    itemsDataChanged = Signal()
    mapParamsChanged = Signal()
    togglesChanged = Signal()

    @Property(list, notify=itemsDataChanged)
    def itemsData(self):
        return self._items_data

    @itemsData.setter
    def itemsData(self, val):
        if self._items_data != val:
            self._items_data = val
            self.itemsDataChanged.emit()
            self.update()

    @Property(float, notify=mapParamsChanged)
    def mapScale(self): return self._map_scale
    @mapScale.setter
    def mapScale(self, val): 
        if self._map_scale != val: self._map_scale = val; self.update()

    @Property(float, notify=mapParamsChanged)
    def mapOffsetX(self): return self._map_offset_x
    @mapOffsetX.setter
    def mapOffsetX(self, val): 
        if self._map_offset_x != val: self._map_offset_x = val; self.update()

    @Property(float, notify=mapParamsChanged)
    def mapOffsetY(self): return self._map_offset_y
    @mapOffsetY.setter
    def mapOffsetY(self, val): 
        if self._map_offset_y != val: self._map_offset_y = val; self.update()

    @Property(float, notify=mapParamsChanged)
    def currentZoom(self): return self._current_zoom
    @currentZoom.setter
    def currentZoom(self, val): 
        if self._current_zoom != val: self._current_zoom = val; self.update()

    @Property(float, notify=mapParamsChanged)
    def centerX(self): return self._center_x
    @centerX.setter
    def centerX(self, val): 
        if self._center_x != val: self._center_x = val; self.update()

    @Property(float, notify=mapParamsChanged)
    def centerY(self): return self._center_y
    @centerY.setter
    def centerY(self, val): 
        if self._center_y != val: self._center_y = val; self.update()

    @Property(bool, notify=togglesChanged)
    def showHexNames(self): return self._show_hex_names
    @showHexNames.setter
    def showHexNames(self, val): 
        if self._show_hex_names != val: self._show_hex_names = val; self.update()

    @Property(bool, notify=togglesChanged)
    def showMajorCities(self): return self._show_major_cities
    @showMajorCities.setter
    def showMajorCities(self, val): 
        if self._show_major_cities != val: self._show_major_cities = val; self.update()

    @Property(bool, notify=togglesChanged)
    def showMinorCities(self): return self._show_minor_cities
    @showMinorCities.setter
    def showMinorCities(self, val): 
        if self._show_minor_cities != val: self._show_minor_cities = val; self.update()

    def paint(self, painter: QPainter):
        if not self._items_data:
            return

        viewport_width = self.width()
        viewport_height = self.height()
        if viewport_width <= 0 or viewport_height <= 0:
            return

        zoomFactor = math.pow(2, self._current_zoom)
        
        # We prepare fonts ahead of time to avoid creating them repeatedly
        # Hex font
        hex_font = QFont("Segoe UI", 11)
        hex_font.setBold(True)
        hex_font.setCapitalization(QFont.AllUppercase)
        if self._current_zoom >= 5:
            hex_font.setPixelSize(36)
        elif self._current_zoom > 2:
            hex_font.setPixelSize(18)
        else:
            hex_font.setPixelSize(11)
        
        # Major font
        major_font = QFont("Segoe UI", 14)
        major_font.setBold(True)
        major_font.setCapitalization(QFont.AllUppercase)
        if self._current_zoom >= 6:
            major_font.setPixelSize(22)
            
        # Minor font
        minor_font = QFont("Segoe UI", 10)
        minor_font.setBold(False)
        minor_font.setCapitalization(QFont.AllUppercase)
        if self._current_zoom >= 6:
            minor_font.setPixelSize(15)

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        # To draw outline, we draw the text shifted or using a QPainterPath.
        # An easy approach for outlining text is to draw it multiple times in black.
        
        for item in self._items_data:
            marker_type = item.get("mapMarkerType", "")
            
            if marker_type == "Hex" and not (self._show_hex_names and self._current_zoom >= 0):
                continue
            if marker_type == "Major" and not (self._show_major_cities and self._current_zoom >= 4):
                continue
            if marker_type == "Minor" and not (self._show_minor_cities and self._current_zoom >= 5):
                continue
                
            text = item.get("text", "")
            if not text:
                continue

            worldPxX = ((item.get("x", 0) * self._map_scale) + self._map_offset_x) * zoomFactor
            worldPxY = ((-item.get("y", 0) * self._map_scale) + self._map_offset_y) * zoomFactor
            
            screenX = worldPxX + (viewport_width / 2) - self._center_x
            screenY = worldPxY + (viewport_height / 2) - self._center_y
            
            # Culling
            if screenX < -200 or screenX > viewport_width + 200 or screenY < -200 or screenY > viewport_height + 200:
                continue
                
            # Setup rendering style
            opacity = 1.0
            color = QColor("#ffffff")
            font = minor_font
            
            if marker_type == "Hex":
                opacity = 0.75
                font = hex_font
            elif marker_type == "Major":
                opacity = 1.0
                font = major_font
            else: # Minor
                opacity = 0.9 if self._current_zoom >= 5 else 0.6
                color = QColor("#dddddd")
                
            painter.setOpacity(opacity)
            painter.setFont(font)
            fm = QFontMetrics(font)
            rect = fm.boundingRect(text)
            
            # Center text around screenX, screenY
            draw_x = screenX - rect.width() / 2
            draw_y = screenY + rect.height() / 4 # Adjusting for baseline offset intuitively
            
            # Draw outline
            painter.setPen(QPen(QColor(0, 0, 0, 200), 2)) # Outline thickness
            # A simple fast outline: draw 4 times slightly shifted
            outline_offset = 1.5
            painter.drawText(draw_x - outline_offset, draw_y, text)
            painter.drawText(draw_x + outline_offset, draw_y, text)
            painter.drawText(draw_x, draw_y - outline_offset, text)
            painter.drawText(draw_x, draw_y + outline_offset, text)
            
            # Draw actual text
            painter.setPen(QColor(color))
            painter.drawText(draw_x, draw_y, text)
