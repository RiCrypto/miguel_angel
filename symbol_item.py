"""
miguel_angel — Graphics Symbol Item
Frontend Developer implementation · Phase 3

QGraphicsItem subclass representing a placed component symbol on the canvas.
Handles:
  - Bounding box rendering (filled rect + label)
  - Pin cross-hair rendering at correct offsets
  - Selection highlight
  - Move + snap-to-grid
  - Context menu (Ask MiguelBot, Properties, Delete, Rotate, Mirror)
  - Data storage for MiguelBot context snapshot
"""

from __future__ import annotations

import math
from typing import Optional

from PyQt6.QtWidgets import (
    QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem,
    QGraphicsEllipseItem, QGraphicsLineItem, QMenu,
    QGraphicsSceneContextMenuEvent,
)
from PyQt6.QtCore  import Qt, QRectF, QPointF
from PyQt6.QtGui   import (
    QPainter, QPen, QBrush, QColor, QFont,
    QFontMetricsF, QAction,
)

from .constants import THEME, CANVAS_GRID_SIZE


# ─── Colour palette (matches canvas theme) ───────────────────────────────────
C_BOX_FILL     = QColor("#EFF6FF")
C_BOX_STROKE   = QColor(THEME["canvas_symbol"])
C_BOX_SEL      = QColor(THEME["canvas_select"])
C_REF_TEXT     = QColor(THEME["text_primary"])
C_SYM_TEXT     = QColor(THEME["canvas_symbol"])
C_PIN          = QColor("#60A5FA")
C_PIN_SEL      = QColor(THEME["canvas_select"])


def snap(value: float, grid: float = CANVAS_GRID_SIZE) -> float:
    return round(value / grid) * grid


class PinItem(QGraphicsItem):
    """
    Small cross-hair drawn at each pin position (relative to parent symbol).
    Drawn in canvas coordinates.
    """

    def __init__(self, x: float, y: float, name: str,
                 pin_type: str, parent: "SymbolItem"):
        super().__init__(parent)
        self._x, self._y = x, y
        self._name       = name
        self._pin_type   = pin_type
        self.setPos(x, y)
        self.setToolTip(f"Pin {name} ({pin_type})")
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable,    False)

    def boundingRect(self) -> QRectF:
        d = 4.0
        return QRectF(-d, -d, d * 2, d * 2)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        parent_sel = self.parentItem() and self.parentItem().isSelected()
        colour = C_PIN_SEL if parent_sel else C_PIN
        pen = QPen(colour, 1.5)
        pen.setCosmetic(True)
        painter.setPen(pen)
        d = 3.0
        painter.drawLine(QPointF(-d, 0), QPointF(d, 0))
        painter.drawLine(QPointF(0, -d), QPointF(0, d))


class SymbolItem(QGraphicsItem):
    """
    Placed component symbol on the schematic canvas.

    Stores component data dict for MiguelBot context snapshot
    and for serialisation back to the Project model.
    """

    # Data role key used to store component dict on the item
    COMPONENT_DATA_ROLE = 0

    def __init__(
        self,
        symbol_id:   str,
        reference:   str,
        width_lu:    float = 4.0,
        height_lu:   float = 4.0,
        pins:        list[dict] | None = None,
        grid_size:   float = CANVAS_GRID_SIZE,
    ):
        super().__init__()

        self._symbol_id   = symbol_id
        self._reference   = reference
        self._width       = width_lu  * grid_size
        self._height      = height_lu * grid_size
        self._grid        = grid_size
        self._rotation_deg = 0.0
        self._pins        = pins or []

        # Flags
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,      True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable,         True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable,       True)
        self.setAcceptHoverEvents(True)

        # Store component data for MiguelBot context
        comp_data = {
            "symbol_id": symbol_id,
            "reference": reference,
            "standard":  self._infer_standard(symbol_id),
            "category":  self._infer_category(symbol_id),
            "position":  {"x": 0, "y": 0},
            "rotation":  0,
        }
        self.setData(self.COMPONENT_DATA_ROLE, comp_data)

        # Draw child items
        self._build_children()

    # ── Build child items ─────────────────────────────────────────────────────

    def _build_children(self) -> None:
        """Build pin cross-hairs as child items."""
        for pin in self._pins:
            px = pin.get("x_offset", 0) * self._grid
            py = pin.get("y_offset", 0) * self._grid
            PinItem(px, py, pin.get("name","?"), pin.get("pin_type","Passive"), self)

    # ── QGraphicsItem overrides ───────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        margin = 6.0
        return QRectF(-margin, -margin,
                      self._width + margin * 2,
                      self._height + margin * 2)

    def shape(self):
        from PyQt6.QtGui import QPainterPath
        path = QPainterPath()
        path.addRect(QRectF(0, 0, self._width, self._height))
        return path

    def paint(self, painter: QPainter, option, widget=None) -> None:
        selected = self.isSelected()

        # Component box
        pen_width = 2.5 if selected else 1.5
        pen = QPen(C_BOX_SEL if selected else C_BOX_STROKE, pen_width)
        pen.setCosmetic(False)
        painter.setPen(pen)
        painter.setBrush(QBrush(C_BOX_FILL))
        painter.drawRoundedRect(QRectF(0, 0, self._width, self._height), 3, 3)

        # Reference label (above box)
        font = QFont("Consolas", 0)
        font.setPointSizeF(max(4.0, self._grid * 0.45))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(C_REF_TEXT))
        ref_rect = QRectF(0, -self._grid * 0.9, self._width, self._grid * 0.85)
        painter.drawText(ref_rect, Qt.AlignmentFlag.AlignCenter, self._reference)

        # Symbol ID below box (smaller)
        font2 = QFont("Consolas", 0)
        font2.setPointSizeF(max(3.0, self._grid * 0.30))
        painter.setFont(font2)
        painter.setPen(QPen(C_SYM_TEXT))
        sym_label = self._symbol_id.split(":")[-1] if ":" in self._symbol_id else self._symbol_id
        id_rect   = QRectF(0, self._height + 1, self._width, self._grid * 0.75)
        painter.drawText(id_rect, Qt.AlignmentFlag.AlignCenter, sym_label)

        # Selection outline glow
        if selected:
            glow_pen = QPen(C_BOX_SEL, 1.0)
            glow_pen.setStyle(Qt.PenStyle.DashLine)
            glow_pen.setCosmetic(True)
            painter.setPen(glow_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(-3, -3, self._width + 6, self._height + 6))

    # ── Snap to grid on move ──────────────────────────────────────────────────

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            snapped_x = snap(value.x(), self._grid)
            snapped_y = snap(value.y(), self._grid)
            new_pos   = QPointF(snapped_x, snapped_y)
            # Update component data position
            data = self.data(self.COMPONENT_DATA_ROLE) or {}
            data["position"] = {
                "x": snapped_x / self._grid,
                "y": snapped_y / self._grid,
            }
            self.setData(self.COMPONENT_DATA_ROLE, data)
            return new_pos
        return super().itemChange(change, value)

    # ── Context menu ──────────────────────────────────────────────────────────

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        menu = QMenu()

        # Style the menu
        menu.setStyleSheet(f"""
            QMenu {{
                background: {THEME['bg_canvas']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border_subtle']};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{ padding: 5px 20px; border-radius: 3px; }}
            QMenu::item:selected {{ background: {THEME['bg_hover']}; }}
            QMenu::separator {{ height:1px; background:{THEME['border_main']}; margin:3px 6px; }}
        """)

        act_miguelbot = menu.addAction("⚡  Ask MiguelBot about " + self._reference)
        act_props     = menu.addAction("⚙  Properties…")
        menu.addSeparator()
        act_rotate    = menu.addAction("↻  Rotate 90°")
        act_mirror    = menu.addAction("↔  Mirror")
        menu.addSeparator()
        act_delete    = menu.addAction("🗑  Delete")

        chosen = menu.exec(event.screenPos())

        if chosen == act_delete:
            scene = self.scene()
            if scene:
                scene.removeItem(self)

        elif chosen == act_rotate:
            self._rotation_deg = (self._rotation_deg + 90) % 360
            self.setRotation(self._rotation_deg)
            data = self.data(self.COMPONENT_DATA_ROLE) or {}
            data["rotation"] = self._rotation_deg
            self.setData(self.COMPONENT_DATA_ROLE, data)

        elif chosen == act_mirror:
            t = self.transform()
            from PyQt6.QtGui import QTransform
            mirror = QTransform(-1, 0, 0, 1, self._width, 0)
            self.setTransform(t * mirror)

        elif chosen == act_miguelbot:
            # Emit to parent window via scene custom event
            scene = self.scene()
            if hasattr(scene, "miguelbot_requested"):
                scene.miguelbot_requested.emit(self._reference, self._symbol_id)

    # ── Hover ─────────────────────────────────────────────────────────────────

    def hoverEnterEvent(self, event) -> None:
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _infer_standard(symbol_id: str) -> str:
        prefix_map = {
            "ISA51": "ISA 5.1", "ISA52": "ISA 5.2",
            "ISA54": "ISA 5.4", "ISA95": "ISA 95",
            "IEC":   "IEC 60617", "ANSI": "ANSI/NEMA", "IEEE": "IEEE 315",
        }
        prefix = symbol_id.split(":")[0] if ":" in symbol_id else ""
        return prefix_map.get(prefix, "Custom")

    @staticmethod
    def _infer_category(symbol_id: str) -> str:
        name = symbol_id.split(":")[-1].upper()
        if any(x in name for x in ["TIC","TI","PI","FI","LI","TT","FCV","PSV","TE","HS"]):
            return "Instrumentation"
        if any(x in name for x in ["CONTACTOR","MOTOR","MCCB","OVERLOAD","XFMR","TERMINAL"]):
            return "Electrical"
        if any(x in name for x in ["PLC","HMI","DCS","SCADA"]):
            return "Control system"
        if any(x in name for x in ["R","C","L","D","NPN","AND","OPAMP"]):
            return "Electronic"
        return "Component"
