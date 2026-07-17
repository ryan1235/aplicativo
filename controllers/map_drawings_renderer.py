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
        self._show_tactical_lines = True
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
        self._inspected_drawing_id = ""
        self._hovered_drawing_id = ""

        # Debounce updates during fast interactions
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(16)
        self._update_timer.timeout.connect(self.update)

        self.setAntialiasing(True)
        self.setOpaquePainting(False)
        self.setRenderTarget(QQuickPaintedItem.Image)

    drawingsChanged = Signal()
    showTacticalLinesChanged = Signal()
    currentDrawingChanged = Signal()
    paramsChanged = Signal()
    dashOffsetChanged = Signal()
    hoveredRouteChanged = Signal()
    inspectedDrawingIdChanged = Signal()
    hoveredDrawingIdChanged = Signal()

    @Property(str, notify=inspectedDrawingIdChanged)
    def inspectedDrawingId(self):
        return self._inspected_drawing_id
    @inspectedDrawingId.setter
    def inspectedDrawingId(self, val):
        if self._inspected_drawing_id != val:
            self._inspected_drawing_id = val
            self.inspectedDrawingIdChanged.emit()
            self.schedule_update()

    @Property(str, notify=hoveredDrawingIdChanged)
    def hoveredDrawingId(self):
        return self._hovered_drawing_id
    @hoveredDrawingId.setter
    def hoveredDrawingId(self, val):
        if self._hovered_drawing_id != val:
            self._hovered_drawing_id = val
            self.hoveredDrawingIdChanged.emit()
            self.schedule_update()

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

    @Property(bool, notify=showTacticalLinesChanged)
    def showTacticalLines(self):
        return self._show_tactical_lines

    @showTacticalLines.setter
    def showTacticalLines(self, val):
        if self._show_tactical_lines != val:
            self._show_tactical_lines = val
            self.showTacticalLinesChanged.emit()
            self.update()
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
    def _draw_shapes_along_path(self, painter, points, viewport_width, viewport_height, shape_type, thickness, color, outlineWidth=0.0, outlineColor=None, shadowColor=None):
        if len(points) < 2: return
        
        spacing = thickness * 5
        if shape_type == "defensive_line": spacing = 40.0
        elif shape_type == "minefield": spacing = 35.0
        elif shape_type == "checkpoint": spacing = 50.0
        
        accumulated_dist = 0.0
        
        for i in range(len(points)-1):
            p1 = points[i]
            p2 = points[i+1]
            x1, y1 = self.worldToCanvas(p1.get("x",0), p1.get("y",0), viewport_width, viewport_height)
            x2, y2 = self.worldToCanvas(p2.get("x",0), p2.get("y",0), viewport_width, viewport_height)
            
            dx = x2 - x1
            dy = y2 - y1
            segment_len = math.hypot(dx, dy)
            if segment_len == 0: continue
            
            ux, uy = dx / segment_len, dy / segment_len
            angle = math.atan2(dy, dx)
            dist_to_next = spacing - accumulated_dist
            
            curr_dist = dist_to_next
            while curr_dist <= segment_len:
                cx = x1 + ux * curr_dist
                cy = y1 + uy * curr_dist
                
                painter.save()
                painter.translate(cx, cy)
                painter.rotate(math.degrees(angle))
                
                size = max(10, thickness * 2)
                
                def draw_shape_with_effects(draw_fn):
                    if shadowColor and outlineWidth > 0:
                        painter.save()
                        painter.translate(2.0, 2.0)
                        draw_fn(shadowColor, thickness + outlineWidth * 2.0 + 2.0)
                        painter.restore()
                    if outlineColor and outlineWidth > 0:
                        draw_fn(outlineColor, thickness + outlineWidth * 2.0)
                    draw_fn(color, thickness)
                
                if shape_type in ["defensive_line", "barricade"]:
                    path = QPainterPath()
                    path.moveTo(-size/2, 0)
                    path.lineTo(size/2, 0)
                    path.lineTo(0, -size)
                    path.lineTo(-size/2, 0)
                    def draw_tri(col, t):
                        painter.setBrush(col)
                        painter.setPen(QPen(col, t/2, Qt.SolidLine))
                        painter.drawPath(path)
                    draw_shape_with_effects(draw_tri)
                elif shape_type == "minefield":
                    def draw_mine(col, t):
                        painter.setPen(QPen(col, t, Qt.SolidLine))
                        painter.drawLine(QPointF(-size/2, -size/2), QPointF(size/2, size/2))
                        painter.drawLine(QPointF(-size/2, size/2), QPointF(size/2, -size/2))
                    draw_shape_with_effects(draw_mine)
                elif shape_type == "checkpoint":
                    def draw_check(col, t):
                        painter.setBrush(col)
                        painter.setPen(QPen(col, t/2, Qt.SolidLine))
                        painter.drawRect(QRectF(-size/2, -size/2, size, size))
                    draw_shape_with_effects(draw_check)
                elif shape_type == "barrier":
                    def draw_bar(col, t):
                        painter.setPen(QPen(col, t, Qt.SolidLine))
                        painter.drawLine(QPointF(0, -size), QPointF(0, size))
                    draw_shape_with_effects(draw_bar)
                    
                painter.restore()
                curr_dist += spacing
                
            accumulated_dist = segment_len - (curr_dist - spacing)

    def drawArrow(self, painter, p1x, p1y, p2x, p2y, headSize, drawShaft=True, outlineWidth=0.0, outlineColor=None, shadowColor=None):
        angle = math.atan2(p2y - p1y, p2x - p1x)
        
        a1x = p2x - headSize * math.cos(angle - math.pi / 6)
        a1y = p2y - headSize * math.sin(angle - math.pi / 6)
        a2x = p2x - headSize * math.cos(angle + math.pi / 6)
        a2y = p2y - headSize * math.sin(angle + math.pi / 6)
        
        path = QPainterPath()
        if drawShaft:
            path.moveTo(p1x, p1y)
            path.lineTo(p2x, p2y)
        path.moveTo(p2x, p2y)
        path.lineTo(a1x, a1y)
        path.lineTo(a2x, a2y)
        path.closeSubpath()
        
        orig_pen = painter.pen()
        
        if shadowColor and outlineWidth > 0:
            painter.save()
            shadow_pen = QPen(orig_pen)
            shadow_pen.setColor(shadowColor)
            shadow_pen.setWidthF(orig_pen.widthF() + outlineWidth * 2.0 + 2.0)
            painter.setPen(shadow_pen)
            painter.translate(2.0, 2.0)
            painter.drawPath(path)
            painter.fillPath(path, shadowColor)
            painter.restore()
            
        if outlineColor and outlineWidth > 0:
            out_pen = QPen(orig_pen)
            out_pen.setColor(outlineColor)
            out_pen.setWidthF(orig_pen.widthF() + outlineWidth * 2.0)
            painter.setPen(out_pen)
            painter.drawPath(path)
            painter.fillPath(path, outlineColor)
            
        painter.setPen(orig_pen)
        painter.drawPath(path)
        painter.fillPath(path, orig_pen.color())

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
            
            if dtype == "brush" and not self._show_tactical_lines:
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
                        
                    lineStyle = d.get("lineStyle", "solid")
                    highlight = d.get("highlight", False)
                    opacity = float(d.get("opacity", 1.0))
                    
                    brush_color = QColor(color_str)
                    if highlight:
                        brush_color.setAlphaF(0.25 * opacity)
                    else:
                        brush_color.setAlphaF(opacity)
                        
                    brush_pen = QPen(brush_color, thickness, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                    if lineStyle == "dashed":
                        brush_pen.setStyle(Qt.CustomDashLine)
                        brush_pen.setDashPattern([6, 6])
                    elif lineStyle == "dotted":
                        brush_pen.setStyle(Qt.CustomDashLine)
                        brush_pen.setDashPattern([1, 4])

                    path = QPainterPath()
                    sx, sy = self.worldToCanvas(points[0].get("x", 0), points[0].get("y", 0), viewport_width, viewport_height)
                    path.moveTo(sx, sy)
                    
                    last_px, last_py = sx, sy
                    for pt in points[1:]:
                        px, py = self.worldToCanvas(pt.get("x", 0), pt.get("y", 0), viewport_width, viewport_height)
                        path.lineTo(px, py)
                        last_px, last_py = px, py
                        
                    d_id = d.get("id") or d.get("_id") or d.get("eventId") or ""
                    is_inspected = (d_id == self._inspected_drawing_id and self._inspected_drawing_id != "")
                    is_hovered = (d_id == self._hovered_drawing_id and self._hovered_drawing_id != "")

                    if is_inspected:
                        # Draw a yellow glow under everything
                        painter.save()
                        glow_pen = QPen(QColor(255, 215, 0, 150), thickness + 12.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                        painter.setPen(glow_pen)
                        painter.drawPath(path)
                        painter.restore()
                        
                    if is_hovered:
                        painter.save()
                        pulse = math.sin(self._dash_offset * 0.2) * 3.0
                        hover_glow_pen = QPen(QColor(255, 255, 255, 200), thickness + 8.0 + max(0, pulse), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                        painter.setPen(hover_glow_pen)
                        painter.drawPath(path)
                        painter.restore()
                        brush_color = brush_color.lighter(150)
                        brush_pen.setColor(brush_color)
                        thickness += 2.0
                        brush_pen.setWidthF(thickness)

                    if not highlight:
                        outlineWidth = max(thickness * 0.20, 2.0)
                        shadowColor = QColor(0, 0, 0, int(70 * opacity))
                        outlineColor = QColor(0, 0, 0, int(255 * opacity)) if brush_color.lightnessF() > 0.4 else QColor(255, 255, 255, int(255 * opacity))
                        
                        if is_inspected:
                            outlineColor = QColor(255, 215, 0, 255)
                            outlineWidth = max(thickness * 0.30, 3.0)
                        elif is_hovered:
                            outlineColor = QColor(255, 255, 255, 255)
                            outlineWidth = max(thickness * 0.40, 4.0)

                        width_in = brush_pen.widthF()
                        is_dashed = brush_pen.style() == Qt.CustomDashLine
                        pattern_in = brush_pen.dashPattern() if is_dashed else []

                        # Draw shadow
                        painter.save()
                        shadow_pen = QPen(brush_pen)
                        shadow_pen.setColor(shadowColor)
                        width_shadow = thickness + outlineWidth * 2.0 + 2.0
                        shadow_pen.setWidthF(width_shadow)
                        if is_dashed and width_shadow > 0:
                            shadow_pen.setDashPattern([p * width_in / width_shadow for p in pattern_in])
                        painter.setPen(shadow_pen)
                        painter.translate(2.0, 2.0)
                        painter.drawPath(path)
                        painter.restore()
                        
                        # Draw outline
                        out_pen = QPen(brush_pen)
                        out_pen.setColor(outlineColor)
                        width_out = thickness + outlineWidth * 2.0
                        out_pen.setWidthF(width_out)
                        if is_dashed and width_out > 0:
                            out_pen.setDashPattern([p * width_in / width_out for p in pattern_in])
                        painter.setPen(out_pen)
                        painter.drawPath(path)
                    
                    painter.setPen(brush_pen)
                    painter.drawPath(path)
                    
                    if d.get("arrowHead", False) or lineStyle in ["advance", "double_movement"]:
                        if len(points) >= 2:
                            pt1 = points[-2]
                            p1x, p1y = self.worldToCanvas(pt1.get("x", 0), pt1.get("y", 0), viewport_width, viewport_height)
                            p2x, p2y = last_px, last_py
                            headSize = max(10.0, thickness * 2.5)
                            self.drawArrow(painter, p1x, p1y, p2x, p2y, headSize, False, outlineWidth, outlineColor, shadowColor)
                            
                    if lineStyle in ["retreat", "double_movement"]:
                        if len(points) >= 2:
                            pt1 = points[1]
                            p1x, p1y = self.worldToCanvas(pt1.get("x", 0), pt1.get("y", 0), viewport_width, viewport_height)
                            p2x, p2y = sx, sy
                            headSize = max(10.0, thickness * 2.5)
                            self.drawArrow(painter, p1x, p1y, p2x, p2y, headSize, False, outlineWidth, outlineColor, shadowColor)
                            
                    if lineStyle in ["barricade", "barrier", "defensive_line", "minefield", "checkpoint"]:
                        self._draw_shapes_along_path(painter, points, viewport_width, viewport_height, lineStyle, thickness, brush_color, outlineWidth, outlineColor, shadowColor)
                            
                    label = d.get("label", "")
                    if label:
                        font = QFont("sans-serif", 12, QFont.Bold)
                        painter.setFont(font)
                        fm = QFontMetrics(font)
                        
                        painter.setPen(QPen(QColor(0, 0, 0, int(255*opacity)), 2))
                        painter.drawText(last_px + 8, last_py + fm.ascent()/2, label)
                        
                        label_color = QColor("#ffffff")
                        label_color.setAlphaF(opacity)
                        painter.setPen(label_color)
                        painter.drawText(last_px + 8, last_py + fm.ascent()/2, label)
                    
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
                        
                    # Intermediate nodes (removed to keep route clean)
                        
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
