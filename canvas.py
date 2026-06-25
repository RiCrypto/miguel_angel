"""
miguel_angel — Schematic Canvas
Frontend Developer implementation · Phase 3

QGraphicsView + QGraphicsScene providing an infinite, zoomable,
pan-able schematic canvas with grid snap.

Signals:
  selectionChanged(list[QGraphicsItem]) → emitted when canvas selection changes
  projectLoaded()                       → emitted when a new project is opened
  ercResultsChanged(list)               → emitted after ERC run

Canvas coordinates are in logical units (1 unit = 1 grid cell = 2.5 mm at 1:1).
"""

from __future__ import annotations

import math
from typing import Optional

from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsLineItem, QGraphicsRectItem, QGraphicsTextItem,
)
from PyQt6.QtCore  import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui   import (
    QPainter, QPen, QColor, QWheelEvent,
    QMouseEvent, QKeyEvent, QTransform,
)

from .constants import CANVAS_GRID_SIZE, CANVAS_SCENE_SIZE, SNAP_GRID, THEME


class SchematicScene(QGraphicsScene):
    """
    QGraphicsScene subclass.
    Holds all component items, wire items, and net labels.
    Emits selectionChanged when the set of selected items changes.
    """

    selectionChanged = pyqtSignal(list)

    def __init__(self, parent=None):
        size = CANVAS_SCENE_SIZE
        super().__init__(-size / 2, -size / 2, size, size, parent)
        self.setBackgroundBrush(QColor(THEME["bg_canvas"]))

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.selectionChanged.emit(self.selectedItems())


class SchematicCanvas(QGraphicsView):
    """
    Main schematic editing canvas.

    Interaction modes (set via set_tool()):
      select   — rubber-band selection + move
      pan      — middle-click or Space+drag
      wire     — click-to-route wire segments
      symbol   — click to place a symbol at cursor
      label    — click to place a net label
      junction — click to place a wire junction
      text     — click to place a text annotation
    """

    # Signals wired to MiguelBot and ERC engine
    selection_changed  = pyqtSignal(list)
    project_loaded     = pyqtSignal()
    erc_results_changed = pyqtSignal(list)
    coordinates_changed = pyqtSignal(float, float)   # cursor x, y in logical units

    # Zoom limits
    MIN_ZOOM = 0.05
    MAX_ZOOM = 20.0
    ZOOM_STEP = 1.15

    def __init__(self, parent=None):
        super().__init__(parent)

        self._scene = SchematicScene(self)
        self.setScene(self._scene)

        # Canvas settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMouseTracking(True)
        self.setBackgroundBrush(QColor(THEME["bg_canvas"]))

        # State
        self._current_tool: str = "select"
        self._zoom_level: float = 1.0
        self._panning: bool = False
        self._pan_start: Optional[QPointF] = None
        self._show_grid: bool = True
        self._snap_enabled: bool = True
        self._wire_in_progress: bool = False
        self._wire_start: Optional[QPointF] = None
        self._wire_preview: Optional[QGraphicsLineItem] = None

        # Symbol placement state
        self._pending_symbol_id: Optional[str] = None
        self._pending_symbol_data: Optional[dict] = None   # {width, height, pins, ref_prefix}
        self._ref_counter: dict[str, int] = {}             # prefix → next number

        # Connect scene
        self._scene.selectionChanged.connect(
            lambda items: self.selection_changed.emit(items)
        )

        # Draw initial grid
        self._draw_grid()

    # ── Grid ──────────────────────────────────────────────────────────────────

    def _draw_grid(self):
        """Draw a dot-grid on the scene background."""
        self._scene.clear()
        if not self._show_grid:
            return

        grid_color = QColor(THEME["canvas_grid"])
        grid_color.setAlphaF(0.12)
        dot_pen = QPen(grid_color)
        dot_pen.setWidth(1)
        dot_pen.setCosmetic(True)

        step = CANVAS_GRID_SIZE
        half = CANVAS_SCENE_SIZE // 2
        rng  = range(-half, half + step, step)
        for x in rng:
            for y in rng:
                item = self._scene.addEllipse(
                    x - 0.5, y - 0.5, 1, 1,
                    dot_pen, QColor(grid_color),
                )
                item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
                item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)

    def set_grid_visible(self, visible: bool):
        self._show_grid = visible
        self._draw_grid()

    def set_snap_enabled(self, enabled: bool):
        self._snap_enabled = enabled

    # ── Symbol placement ──────────────────────────────────────────────────────

    def set_pending_symbol(self, symbol_id: str, symbol_data: dict) -> None:
        """
        Arm the canvas to place a symbol on the next click.
        Called by mainwindow when user double-clicks a library item.

        symbol_data must contain:
          width_lu, height_lu, pins (list of dicts), reference_prefix
        """
        self._pending_symbol_id   = symbol_id
        self._pending_symbol_data = symbol_data
        self.set_tool("symbol")
        self.setCursor(Qt.CursorShape.CrossCursor)

    def _place_symbol(self, pos: QPointF) -> None:
        """Place the pending symbol at the snapped canvas position."""
        if not self._pending_symbol_id or not self._pending_symbol_data:
            return

        from .symbol_item import SymbolItem

        data     = self._pending_symbol_data
        prefix   = data.get("reference_prefix", "X")
        count    = self._ref_counter.get(prefix, 1)
        ref      = f"{prefix}{count}"
        self._ref_counter[prefix] = count + 1

        item = SymbolItem(
            symbol_id  = self._pending_symbol_id,
            reference  = ref,
            width_lu   = data.get("width_lu",  4.0),
            height_lu  = data.get("height_lu", 4.0),
            pins       = data.get("pins", []),
            grid_size  = CANVAS_GRID_SIZE,
        )
        item.setPos(pos)
        self._scene.addItem(item)
        self._scene.clearSelection()
        item.setSelected(True)

        # Emit selection so Properties panel updates immediately
        self.selection_changed.emit([item])

        # Stay in symbol tool for rapid sequential placement
        # Press Escape to return to Select

    def cancel_pending_symbol(self) -> None:
        """Cancel symbol placement mode."""
        self._pending_symbol_id   = None
        self._pending_symbol_data = None

    # ── Tool ──────────────────────────────────────────────────────────────────

    def set_tool(self, tool: str):
        self._current_tool = tool
        self._cancel_wire_in_progress()

        if tool == "select":
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif tool == "pan":
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        elif tool in ("wire", "symbol", "label", "junction", "text", "power", "ground"):
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.CrossCursor)

    # ── Coordinate helpers ────────────────────────────────────────────────────

    def _snap(self, pos: QPointF) -> QPointF:
        """Snap a scene position to the nearest grid point."""
        if not self._snap_enabled:
            return pos
        g = CANVAS_GRID_SIZE
        return QPointF(round(pos.x() / g) * g, round(pos.y() / g) * g)

    def scene_to_logical(self, pos: QPointF) -> tuple[float, float]:
        """Convert scene coordinates to logical schematic units."""
        return pos.x() / CANVAS_GRID_SIZE, pos.y() / CANVAS_GRID_SIZE

    def get_context_snapshot(self) -> dict:
        """
        Return a snapshot of the current canvas state for MiguelBot.
        Called by the MiguelBot panel on every query.
        """
        selected = self._scene.selectedItems()
        comp_info = []
        for item in selected:
            data = item.data(0)
            if isinstance(data, dict):
                comp_info.append(data)

        return {
            "selected_components": comp_info,
            "active_nets":  [],
            "erc_errors":   [],
            "zoom_level":   round(self._zoom_level * 100),
            "tool":         self._current_tool,
        }

    # ── Zoom ──────────────────────────────────────────────────────────────────

    def zoom_in(self):
        self._set_zoom(self._zoom_level * self.ZOOM_STEP)

    def zoom_out(self):
        self._set_zoom(self._zoom_level / self.ZOOM_STEP)

    def zoom_fit(self):
        items = [i for i in self._scene.items()
                 if i.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable]
        if items:
            rect = self._scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
            self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        else:
            self.resetTransform()
        self._zoom_level = self.transform().m11()

    def zoom_100(self):
        self._set_zoom(1.0)

    def _set_zoom(self, level: float):
        level = max(self.MIN_ZOOM, min(self.MAX_ZOOM, level))
        self.resetTransform()
        self.scale(level, level)
        self._zoom_level = level

    @property
    def zoom_percent(self) -> int:
        return round(self._zoom_level * 100)

    # ── Wire drawing ──────────────────────────────────────────────────────────

    def _cancel_wire_in_progress(self):
        if self._wire_preview:
            self._scene.removeItem(self._wire_preview)
            self._wire_preview = None
        self._wire_in_progress = False
        self._wire_start = None

    def _start_wire(self, pos: QPointF):
        self._wire_in_progress = True
        self._wire_start = pos
        pen = QPen(QColor(THEME["canvas_wire"]))
        pen.setWidth(2)
        pen.setCosmetic(True)
        self._wire_preview = self._scene.addLine(
            pos.x(), pos.y(), pos.x(), pos.y(), pen
        )

    def _update_wire_preview(self, pos: QPointF):
        if not self._wire_preview or not self._wire_start:
            return
        sx, sy = self._wire_start.x(), self._wire_start.y()
        ex, ey = pos.x(), pos.y()
        # Orthogonal snap: extend along the dominant axis
        if abs(ex - sx) >= abs(ey - sy):
            ey = sy
        else:
            ex = sx
        self._wire_preview.setLine(sx, sy, ex, ey)

    def _finish_wire(self, pos: QPointF):
        self._cancel_wire_in_progress()
        # TODO Phase 3: commit wire to model and re-run netlist

    # ── Qt events ─────────────────────────────────────────────────────────────

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def mousePressEvent(self, event: QMouseEvent):
        scene_pos = self.mapToScene(event.pos())
        snapped   = self._snap(scene_pos)

        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if self._current_tool == "symbol":
            self._place_symbol(snapped)
            return

        if self._current_tool == "wire":
            if not self._wire_in_progress:
                self._start_wire(snapped)
            else:
                self._finish_wire(snapped)
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        scene_pos = self.mapToScene(event.pos())
        snapped   = self._snap(scene_pos)
        lx, ly    = self.scene_to_logical(snapped)
        self.coordinates_changed.emit(lx, ly)

        if self._panning and self._pan_start:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            return

        if self._current_tool == "wire" and self._wire_in_progress:
            self._update_wire_preview(snapped)
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            if self._current_tool == "pan":
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self._cancel_wire_in_progress()
            self.cancel_pending_symbol()
            self.set_tool("select")
        elif event.key() == Qt.Key.Key_Space:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        elif event.key() == Qt.Key.Key_Delete:
            for item in self._scene.selectedItems():
                self._scene.removeItem(item)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Space:
            self.set_tool(self._current_tool)
        super().keyReleaseEvent(event)
