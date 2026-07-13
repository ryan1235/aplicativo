import math
from PySide6.QtQuick import QQuickPaintedItem
from PySide6.QtCore import Property, Slot, Signal, Qt, QRectF, QPointF, QTimer
from PySide6.QtGui import QPainter, QFont, QPen, QColor, QFontMetrics, QPainterPath

class MapDrawingsRenderer(QQuickPaintedItem):
    """
    High-performance C++ backend renderer for map drawings (Canvas replacement).
    Draws brushes, arrows, polygons, routes, and artillery indicators using QPainter.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._drawings = []
        self._current_drawing = {}
        self._dash_offset = 0.0
        self._map_scale = 1.0
        self._map_offset_x = 0.0
        self._map_offset_y = 0.0
        self._current_zoom = 0.0
        self._center_x = 0.0
        self._center_y = 0.0
        self._map_zoom_scale_x = 4.0
        self._map_zoom_scale_y = 4.0

        # Debounce updates during fast interactions
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(16)
        self._update_timer.timeout.connect(self.update)

        self.setAntialiasing(True)
        self.setOpaquePainting(False)
        self.setRenderTarget(QQuickPaintedItem.Image)

    drawingsChanged = Signal()
    currentDrawingChanged = Signal()
    paramsChanged = Signal()
    dashOffsetChanged = Signal()
    hoveredRouteChanged = Signal()

    @Property(list, notify=drawingsChanged)
    def drawings(self):
        return self._drawings
    @drawings.setter
    def drawings(self, val):
        if hasattr(val, 'toVariant'):
            val = val.toVariant()
        self._drawings = val if isinstance(val, list) else list(val) if val else []
        self.drawingsChanged.emit()
        self.schedule_update()

    @Property('QVariant', notify=currentDrawingChanged)
    def currentDrawing(self):
        return self._current_drawing
        
    @currentDrawing.setter
    def currentDrawing(self, val):
        if hasattr(val, 'toVariant'):
            val = val.toVariant()
        self._current_drawing = val if isinstance(val, dict) else dict(val) if val else {}
        self.currentDrawingChanged.emit()
        self.schedule_update()

    @Property(float, notify=dashOffsetChanged)
    def dashOffset(self):
        return self._dash_offset
    @dashOffset.setter
    def dashOffset(self, val):
        if self._dash_offset != val:
            self._dash_offset = val
            self.dashOffsetChanged.emit()
            self.schedule_update()

    _hovered_route = {}
    @Property(dict, notify=hoveredRouteChanged)
    def hoveredRoute(self):
        return self._hovered_route
    @hoveredRoute.setter
    def hoveredRoute(self, val):
        self._hovered_route = val
        self.hoveredRouteChanged.emit()
        self.schedule_update()

    @Property(float, notify=paramsChanged)
    def mapScale(self):
        return self._map_scale
    @mapScale.setter
    def mapScale(self, val):
        if self._map_scale != val:
            self._map_scale = val
            self.schedule_update()

    @Property(float, notify=paramsChanged)
    def mapOffsetX(self):
        return self._map_offset_x
    @mapOffsetX.setter
    def mapOffsetX(self, val):
        if self._map_offset_x != val:
            self._map_offset_x = val
            self.schedule_update()

    @Property(float, notify=paramsChanged)
    def mapOffsetY(self):
        return self._map_offset_y
    @mapOffsetY.setter
    def mapOffsetY(self, val):
        if self._map_offset_y != val:
            self._map_offset_y = val
            self.schedule_update()

    @Property(float, notify=paramsChanged)
    def currentZoom(self):
        return self._current_zoom
    @currentZoom.setter
    def currentZoom(self, val):
        if self._current_zoom != val:
            self._current_zoom = val
            self.schedule_update()

    @Property(float, notify=paramsChanged)
    def centerX(self):
        return self._center_x
    @centerX.setter
    def centerX(self, val):
        if self._center_x != val:
            self._center_x = val
            self.schedule_update()

    @Property(float, notify=paramsChanged)
    def centerY(self):
        return self._center_y
    @centerY.setter
    def centerY(self, val):
        if self._center_y != val:
            self._center_y = val
            self.schedule_update()

    @Property(float, notify=paramsChanged)
    def mapZoomScaleX(self):
        return self._map_zoom_scale_x
    @mapZoomScaleX.setter
    def mapZoomScaleX(self, val):
        if self._map_zoom_scale_x != val:
            self._map_zoom_scale_x = val
            self.schedule_update()

    @Property(float, notify=paramsChanged)
    def mapZoomScaleY(self):
        return self._map_zoom_scale_y
    @mapZoomScaleY.setter
    def mapZoomScaleY(self, val):
        if self._map_zoom_scale_y != val:
            self._map_zoom_scale_y = val
            self.schedule_update()

    def schedule_update(self):
        self.update()

    def _points_in_view(self, points, viewport_width, viewport_height, margin=64):
        left = -margin
        right = viewport_width + margin
        top = -margin
        bottom = viewport_height + margin
        for pt in points:
            px, py = self.worldToCanvas(pt.get("x", 0), pt.get("y", 0), viewport_width, viewport_height)
            if left <= px <= right and top <= py <= bottom:
                return True
        return False

    def worldToCanvas(self, wx, wy, viewport_width, viewport_height, zoomFactorX=None, zoomFactorY=None):
        zoomFactor = 2 ** (self._current_zoom - 6)
        mapX = wx * zoomFactor
        mapY = wy * zoomFactor
        sx_screen = mapX + (viewport_width / 2) - self._center_x
        sy_screen = mapY + (viewport_height / 2) - self._center_y
        return sx_screen, sy_screen

    def apiToWorld(self, apiX, apiY):
        wX = apiX * 80.0
        wY = -apiY * 80.0 - 4024.0
        return wX, wY

    def drawArrow(self, painter, p1x, p1y, p2x, p2y, headSize):
        angle = math.atan2(p2y - p1y, p2x - p1x)
        painter.drawLine(QPointF(p1x, p1y), QPointF(p2x, p2y))
        
        a1x = p2x - headSize * math.cos(angle - math.pi / 6)
        a1y = p2y - headSize * math.sin(angle - math.pi / 6)
        a2x = p2x - headSize * math.cos(angle + math.pi / 6)
        a2y = p2y - headSize * math.sin(angle + math.pi / 6)
        
        path = QPainterPath()
        path.moveTo(p2x, p2y)
        path.lineTo(a1x, a1y)
        path.lineTo(a2x, a2y)
        path.closeSubpath()
        painter.drawPath(path)
        painter.fillPath(path, painter.pen().color())

    def paint(self, painter: QPainter):
        viewport_width = self.width()
        viewport_height = self.height()
        if viewport_width <= 0 or viewport_height <= 0:
            return

        all_drawings = list(self._drawings) if self._drawings else []
        if self._current_drawing:
            all_drawings.append(self._current_drawing)
            
        if not all_drawings:
            return

        zoomFactorX = self._map_zoom_scale_x
        zoomFactorY = self._map_zoom_scale_y
        painter.setRenderHint(QPainter.Antialiasing)

        for d in all_drawings:
            if not isinstance(d, dict):
                continue
                
            dtype = d.get("type", "")
            if not dtype:
                continue
                
            color_str = d.get("color", "#3b82f6")
            thickness = float(d.get("thickness", 3))
            
            color = QColor(color_str)
            pen = QPen(color, thickness, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            
            if dtype == "brush":
                points = d.get("points", [])
                if len(points) > 1:
                    if not self._points_in_view(points, viewport_width, viewport_height):
                        continue
                    path = QPainterPath()
                    sx, sy = self.worldToCanvas(points[0].get("x", 0), points[0].get("y", 0), viewport_width, viewport_height)
                    path.moveTo(sx, sy)
                    for pt in points[1:]:
                        px, py = self.worldToCanvas(pt.get("x", 0), pt.get("y", 0), viewport_width, viewport_height)
                        path.lineTo(px, py)
                    painter.drawPath(path)
                    
            elif dtype == "arrow":
                start = d.get("start")
                end = d.get("end")
                if start and end:
                    p1x, p1y = self.worldToCanvas(start.get("x", 0), start.get("y", 0), viewport_width, viewport_height)
                    p2x, p2y = self.worldToCanvas(end.get("x", 0), end.get("y", 0), viewport_width, viewport_height)
                    headSize = 10 + thickness * 1.5
                    self.drawArrow(painter, p1x, p1y, p2x, p2y, headSize)
                    
            elif dtype == "polygon":
                points = d.get("points", [])
                if len(points) > 0:
                    if not self._points_in_view(points, viewport_width, viewport_height):
                        continue
                    path = QPainterPath()
                    sx, sy = self.worldToCanvas(points[0].get("x", 0), points[0].get("y", 0), viewport_width, viewport_height)
                    path.moveTo(sx, sy)
                    for pt in points[1:]:
                        px, py = self.worldToCanvas(pt.get("x", 0), pt.get("y", 0), viewport_width, viewport_height)
                        path.lineTo(px, py)
                    if len(points) > 2:
                        path.closeSubpath()
                        fill_color = QColor(color)
                        fill_color.setAlphaF(0.3)
                        painter.fillPath(path, fill_color)
                        
                    painter.drawPath(path)
                    
                    name = d.get("name", "")
                    if name and len(points) > 0:
                        cx, cy = 0.0, 0.0
                        for pt in points:
                            px, py = self.worldToCanvas(pt.get("x", 0), pt.get("y", 0), viewport_width, viewport_height)
                            cx += px
                            cy += py
                        cx /= len(points)
                        cy /= len(points)
                        
                        font = QFont("sans-serif", 14, QFont.Bold)
                        painter.setFont(font)
                        fm = QFontMetrics(font)
                        txtWidth = fm.horizontalAdvance(name)
                        
                        painter.setPen(Qt.NoPen)
                        # Background outline effect for polygon name
                        painter.setPen(QPen(QColor(0, 0, 0), 3))
                        painter.drawText(cx - txtWidth/2, cy + fm.ascent()/2 - fm.height()/2, name)
                        painter.setPen(QColor("#ffffff"))
                        painter.drawText(cx - txtWidth/2, cy + fm.ascent()/2 - fm.height()/2, name)
                        
            elif dtype == "route":
                points = d.get("points", [])
                if len(points) > 0:
                    if not self._points_in_view(points, viewport_width, viewport_height):
                        continue
                    path = QPainterPath()
                    start_px, start_py = self.worldToCanvas(points[0].get("x", 0), points[0].get("y", 0), viewport_width, viewport_height)
                    path.moveTo(start_px, start_py)
                    for pt in points[1:]:
                        px, py = self.worldToCanvas(pt.get("x", 0), pt.get("y", 0), viewport_width, viewport_height)
                        path.lineTo(px, py)
                        
                    # Custom dash pattern
                    dash_pen = QPen(color, thickness, Qt.CustomDashLine, Qt.RoundCap, Qt.RoundJoin)
                    dash_pen.setDashPattern([8, 6])
                    dash_pen.setDashOffset(-self._dash_offset)
                    painter.setPen(dash_pen)
                    painter.drawPath(path)
                    
                    # Reset pen for indicators
                    solid_pen = QPen(color, 1.5, Qt.SolidLine)
                    
                    # Start Indicator A
                    startPulse = 10 + math.sin(self._dash_offset * 0.15) * 1.5
                    
                    pulse_color = QColor(255, 255, 255, 51) if color_str == "#ffffff" else QColor(59, 130, 246, 63)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(pulse_color)
                    painter.drawEllipse(QPointF(start_px, start_py), startPulse + 3, startPulse + 3)
                    
                    painter.setBrush(color)
                    painter.setPen(QPen(QColor("#ffffff"), 2))
                    painter.drawEllipse(QPointF(start_px, start_py), 10, 10)
                    
                    font = QFont("sans-serif", 11, QFont.Bold)
                    painter.setFont(font)
                    fm = QFontMetrics(font)
                    text_color = QColor("#111827") if color_str in ("#ffffff", "#eab308") else QColor("#ffffff")
                    painter.setPen(text_color)
                    painter.drawText(start_px - fm.horizontalAdvance("A")/2, start_py + fm.ascent()/2 - fm.height()/2 + 1, "A")
                    
                    # End Indicator B
                    if len(points) > 1:
                        end_px, end_py = self.worldToCanvas(points[-1].get("x", 0), points[-1].get("y", 0), viewport_width, viewport_height)
                        endPulse = 10 + math.cos(self._dash_offset * 0.15) * 1.5
                        painter.setPen(Qt.NoPen)
                        painter.setBrush(pulse_color)
                        painter.drawEllipse(QPointF(end_px, end_py), endPulse + 3, endPulse + 3)
                        
                        painter.setBrush(color)
                        painter.setPen(QPen(QColor("#ffffff"), 2))
                        painter.drawEllipse(QPointF(end_px, end_py), 10, 10)
                        
                        painter.setPen(text_color)
                        painter.drawText(end_px - fm.horizontalAdvance("B")/2, end_py + fm.ascent()/2 - fm.height()/2 + 1, "B")
                        
                    # Intermediate nodes
                    painter.setBrush(QColor("#ffffff"))
                    painter.setPen(solid_pen)
                    for pt in points[1:-1]:
                        px, py = self.worldToCanvas(pt.get("x", 0), pt.get("y", 0), viewport_width, viewport_height)
                        painter.drawEllipse(QPointF(px, py), 4, 4)
                        
                    # Route Name
                    name = d.get("name", "")
                    if name:
                        cx, cy = 0.0, 0.0
                        for pt in points:
                            px, py = self.worldToCanvas(pt.get("x", 0), pt.get("y", 0), viewport_width, viewport_height)
                            cx += px
                            cy += py
                        cx /= len(points)
                        cy /= len(points)
                        
                        font = QFont("sans-serif", 12, QFont.Bold)
                        painter.setFont(font)
                        fm = QFontMetrics(font)
                        txtWidth = fm.horizontalAdvance(name)
                        
                        bg_rect = QRectF(cx - txtWidth/2 - 8, cy - 10, txtWidth + 16, 20)
                        painter.setBrush(QColor(10, 15, 24, 216))
                        painter.setPen(QPen(color, 1))
                        painter.drawRect(bg_rect)
                        
                        painter.setPen(QColor("#ffffff"))
                        painter.drawText(cx - txtWidth/2, cy + fm.ascent()/2 - fm.height()/2, name)
                        
            elif dtype == "artillery":
                start = d.get("start")
                end = d.get("end")
                if start and end:
                    wx1, wy1 = self.apiToWorld(start.get("x", 0), start.get("y", 0))
                    wx2, wy2 = self.apiToWorld(end.get("x", 0), end.get("y", 0))
                    if not self._points_in_view([{"x": wx1, "y": wy1}, {"x": wx2, "y": wy2}], viewport_width, viewport_height):
                        continue
                    aP1x, aP1y = self.worldToCanvas(wx1, wy1, viewport_width, viewport_height)
                    aP2x, aP2y = self.worldToCanvas(wx2, wy2, viewport_width, viewport_height)
                    
                    art_color = QColor(d.get("color", "#ef4444"))
                    art_pen = QPen(art_color, thickness, Qt.CustomDashLine)
                    art_pen.setDashPattern([5, 5])
                    painter.setPen(art_pen)
                    painter.drawLine(QPointF(aP1x, aP1y), QPointF(aP2x, aP2y))
                    
                    # Crosshair end
                    painter.setPen(QPen(art_color, thickness))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawEllipse(QPointF(aP2x, aP2y), 8, 8)
                    painter.drawLine(QPointF(aP2x - 12, aP2y), QPointF(aP2x + 12, aP2y))
                    painter.drawLine(QPointF(aP2x, aP2y - 12), QPointF(aP2x, aP2y + 12))
                    
                    # Range circle around start
                    dist_api = math.sqrt((end.get("x", 0) - start.get("x", 0))**2 + (end.get("y", 0) - start.get("y", 0))**2)
                    radius_world = dist_api * self._map_scale
                    radius_screen = radius_world * zoomFactorX
                    
                    painter.setPen(QPen(QColor(239, 68, 68, 127), 1, Qt.DashLine))
                    painter.drawEllipse(QPointF(aP1x, aP1y), radius_screen, radius_screen)
                    
                    info = d.get("info", "")
                    if info:
                        aCx = (aP1x + aP2x) / 2
                        aCy = (aP1y + aP2y) / 2
                        font = QFont("sans-serif", 13, QFont.Bold)
                        painter.setFont(font)
                        fm = QFontMetrics(font)
                        aTxtW = fm.horizontalAdvance(info)
                        
                        painter.setPen(Qt.NoPen)
                        painter.setBrush(QColor(0, 0, 0, 178)) # 0.7 alpha
                        painter.drawRect(QRectF(aCx - aTxtW / 2 - 4, aCy - 10, aTxtW + 8, 20))
                        
                        painter.setPen(QColor("#ffffff"))
                        painter.drawText(aCx - aTxtW / 2, aCy + fm.ascent() / 2 - fm.height() / 2 + 1, info)
                        
            elif dtype == "parabola":
                start = d.get("start")
                end = d.get("end")
                if start and end:
                    wx1, wy1 = self.apiToWorld(start.get("x", 0), start.get("y", 0))
                    wx2, wy2 = self.apiToWorld(end.get("x", 0), end.get("y", 0))
                    if not self._points_in_view([{"x": wx1, "y": wy1}, {"x": wx2, "y": wy2}], viewport_width, viewport_height):
                        continue
                    sPx, sPy = self.worldToCanvas(wx1, wy1, viewport_width, viewport_height)
                    ePx, ePy = self.worldToCanvas(wx2, wy2, viewport_width, viewport_height)
                    
                    cx = (sPx + ePx) / 2
                    cy = (sPy + ePy) / 2
                    dx = ePx - sPx
                    dy = ePy - sPy
                    ctrlX = cx - dy * 0.3
                    ctrlY = cy + dx * 0.3
                    
                    isHovered = False
                    if self._hovered_route and self._hovered_route.get("start") and self._hovered_route.get("end"):
                        hr_s = self._hovered_route["start"]
                        hr_e = self._hovered_route["end"]
                        if abs(hr_s.get("x", 0) - start.get("x", 0)) < 0.1 and abs(hr_e.get("x", 0) - end.get("x", 0)) < 0.1:
                            isHovered = True
                            
                    # Glowing background path
                    bg_path = QPainterPath()
                    bg_path.moveTo(sPx, sPy)
                    bg_path.quadTo(ctrlX, ctrlY, ePx, ePy)
                    painter.setPen(QPen(QColor(234, 179, 8, 89) if isHovered else QColor(59, 130, 246, 76), 10 if isHovered else 6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                    painter.drawPath(bg_path)
                    
                    # Dotted foreground path
                    fg_pen = QPen(QColor("#eab308") if isHovered else color, 4.5 if isHovered else 2.5, Qt.CustomDashLine, Qt.RoundCap, Qt.RoundJoin)
                    fg_pen.setDashPattern([8, 6])
                    fg_pen.setDashOffset(-self._dash_offset)
                    painter.setPen(fg_pen)
                    painter.drawPath(bg_path)
                    
                    # Origin waypoint
                    painter.setPen(QPen(QColor("#ffffff"), 1.5))
                    painter.setBrush(QColor("#eab308") if isHovered else color)
                    painter.drawEllipse(QPointF(sPx, sPy), 7, 7)
                    painter.setBrush(QColor("#ffffff"))
                    painter.drawEllipse(QPointF(sPx, sPy), 2.5, 2.5)
                    
                    # Arrowhead
                    headlen = 14 + thickness
                    angle = math.atan2(ePy - ctrlY, ePx - ctrlX)
                    
                    arrow_path = QPainterPath()
                    arrow_path.moveTo(ePx, ePy)
                    arrow_path.lineTo(ePx - headlen * math.cos(angle - math.pi / 6), ePy - headlen * math.sin(angle - math.pi / 6))
                    arrow_path.lineTo(ePx - headlen * math.cos(angle + math.pi / 6), ePy - headlen * math.sin(angle + math.pi / 6))
                    arrow_path.closeSubpath()
                    
                    painter.setBrush(QColor("#eab308") if isHovered else color)
                    painter.drawPath(arrow_path)
                    
            elif dtype == "text":
                start = d.get("start")
                text_val = d.get("text", "")
                if start and text_val:
                    tPx, tPy = self.worldToCanvas(start.get("x", 0), start.get("y", 0), viewport_width, viewport_height)
                    
                    font = QFont("sans-serif", 12, QFont.Bold)
                    painter.setFont(font)
                    fm = QFontMetrics(font)
                    tTxtW = fm.horizontalAdvance(text_val)
                    tTxtH = fm.height()
                    
                    rect_x = tPx + 15
                    rect_y = tPy - (tTxtH + 8) / 2
                    
                    # Connector line
                    painter.setPen(QPen(color, 2, Qt.SolidLine))
                    painter.drawLine(QPointF(tPx, tPy), QPointF(rect_x, tPy))
                    
                    # Center dot (at snapping point)
                    painter.setBrush(color)
                    painter.setPen(QPen(QColor("#ffffff"), 1.5))
                    painter.drawEllipse(QPointF(tPx, tPy), 5, 5)
                    
                    # Background rect
                    painter.setBrush(QColor("#ffffff"))
                    painter.setPen(QPen(color, 2))
                    painter.drawRect(QRectF(rect_x, rect_y, tTxtW + 16, tTxtH + 8))
                    
                    # Text inside
                    painter.setPen(color)
                    painter.drawText(rect_x + 8, rect_y + fm.ascent() + 4, text_val)
