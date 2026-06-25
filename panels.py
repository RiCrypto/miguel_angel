"""
miguel_angel — Dockable Side Panels
Frontend Developer implementation · Phase 3

Four dock panels:
  ProjectNavigatorPanel  — left · project tree (sheets, assets)
  ComponentLibraryPanel  — right · symbol browser with search
  PropertiesPanel        — right · selected component properties
  MiguelBotPanel         — right · AI assistant (placeholder; full impl Phase 3)
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem,
    QLineEdit, QLabel, QPushButton, QFrame, QTextEdit,
    QSizePolicy, QScrollArea, QFormLayout,
)
from PyQt6.QtCore  import Qt, pyqtSignal, QSize
from PyQt6.QtGui   import QFont, QColor

from .constants import THEME


def _label(text: str, muted: bool = False) -> QLabel:
    lbl = QLabel(text)
    if muted:
        lbl.setStyleSheet(f"color: {THEME['text_muted']}; font-size: 11px;")
    return lbl


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        f"color: {THEME['text_muted']}; font-size: 10px; "
        f"letter-spacing: 1px; padding: 8px 10px 4px;"
    )
    return lbl


# ─────────────────────────────────────────────────────────────────────────────
# Project Navigator
# ─────────────────────────────────────────────────────────────────────────────

class ProjectNavigatorPanel(QDockWidget):
    """
    Left dock — displays the project tree:
      Sheets (Sheet 1, Sheet 2, …)
      Assets (Components, Line types)
    """

    sheet_selected = pyqtSignal(str)   # emits sheet name

    def __init__(self, parent=None):
        super().__init__("Project", parent)
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.setMinimumWidth(180)
        self.setMaximumWidth(300)
        self._build()

    def _build(self):
        root = QWidget()
        root.setStyleSheet(f"background: {THEME['bg_panel']};")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(14)
        self._tree.setStyleSheet(
            f"QTreeWidget {{ background: {THEME['bg_panel']}; border: none; }}"
        )
        self._tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._tree)

        self.setWidget(root)
        self.load_project(None)

    def load_project(self, project):
        self._tree.clear()

        sheets_root = QTreeWidgetItem(["Sheets"])
        sheets_root.setFont(0, QFont("Segoe UI", 11, QFont.Weight.Medium))
        for name in (["Sheet 1"] if project is None else
                     [s.name for s in project.sheets]):
            item = QTreeWidgetItem([name])
            item.setData(0, Qt.ItemDataRole.UserRole, ("sheet", name))
            sheets_root.addChild(item)

        assets_root = QTreeWidgetItem(["Assets"])
        assets_root.setFont(0, QFont("Segoe UI", 11, QFont.Weight.Medium))
        for name in ["Components", "Line types", "Nets"]:
            assets_root.addChild(QTreeWidgetItem([name]))

        self._tree.addTopLevelItems([sheets_root, assets_root])
        self._tree.expandAll()

    def _on_item_clicked(self, item: QTreeWidgetItem, _col: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data[0] == "sheet":
            self.sheet_selected.emit(data[1])


# ─────────────────────────────────────────────────────────────────────────────
# Component Library Panel
# ─────────────────────────────────────────────────────────────────────────────

class ComponentLibraryPanel(QDockWidget):
    """
    Right dock — searchable symbol browser.
    Grouped by standard and category.
    symbol_selected emitted when user clicks a symbol.
    """

    symbol_selected = pyqtSignal(str)   # emits symbol_id

    def __init__(self, library_db=None, parent=None):
        super().__init__("Component library", parent)
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.setMinimumWidth(220)
        self.setMaximumWidth(360)
        self._db = library_db
        self._build()
        if self._db:
            self._load_all()

    def _build(self):
        root = QWidget()
        root.setStyleSheet(f"background: {THEME['bg_panel']};")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(6)

        # Search
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search symbols…")
        self._search.textChanged.connect(self._on_search)
        layout.addWidget(self._search)

        # Symbol tree
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(12)
        self._tree.setStyleSheet(
            f"QTreeWidget {{ background: {THEME['bg_panel']}; border: none; }}"
        )
        self._tree.itemDoubleClicked.connect(self._on_select)
        layout.addWidget(self._tree)

        # Place button
        self._btn_place = QPushButton("Place symbol →")
        self._btn_place.setEnabled(False)
        self._btn_place.clicked.connect(self._on_place)
        layout.addWidget(self._btn_place)

        self.setWidget(root)

    def _load_all(self):
        self._tree.clear()
        standards = [
            "ISA 5.1", "ISA 5.2", "ISA 5.4", "ISA 95",
            "IEC 60617", "ANSI/NEMA", "IEEE 315",
        ]
        for std in standards:
            std_item = QTreeWidgetItem([std])
            std_item.setFont(0, QFont("Segoe UI", 11, QFont.Weight.Medium))
            syms = self._db.get_symbols_by_standard(std) if self._db else []
            for sym in syms:
                child = QTreeWidgetItem([f"{sym.reference_prefix}  {sym.name}"])
                child.setData(0, Qt.ItemDataRole.UserRole, sym.symbol_id)
                child.setToolTip(0, sym.description or "")
                std_item.addChild(child)
            if syms or not self._db:
                self._tree.addTopLevelItem(std_item)

        if not self._db:
            placeholder = QTreeWidgetItem(["(Library not connected)"])
            self._tree.addTopLevelItem(placeholder)

    def _on_search(self, query: str):
        if not query:
            self._load_all()
            return
        if not self._db:
            return
        self._tree.clear()
        results = self._db.search(query, limit=30)
        results_item = QTreeWidgetItem([f"Results ({len(results)})"])
        for sym in results:
            child = QTreeWidgetItem([f"{sym.reference_prefix}  {sym.name}"])
            child.setData(0, Qt.ItemDataRole.UserRole, sym.symbol_id)
            child.setToolTip(0, sym.description or "")
            results_item.addChild(child)
        self._tree.addTopLevelItem(results_item)
        results_item.setExpanded(True)

    def _on_select(self, item: QTreeWidgetItem, _col: int):
        sid = item.data(0, Qt.ItemDataRole.UserRole)
        if sid:
            self._btn_place.setEnabled(True)
            self._btn_place.setProperty("pending_sid", sid)

    def _on_place(self):
        sid = self._btn_place.property("pending_sid")
        if sid:
            self.symbol_selected.emit(sid)


# ─────────────────────────────────────────────────────────────────────────────
# Properties Panel
# ─────────────────────────────────────────────────────────────────────────────

class PropertiesPanel(QDockWidget):
    """
    Right dock — shows properties of the currently selected component.
    Updates automatically via canvas.selection_changed signal.
    """

    def __init__(self, parent=None):
        super().__init__("Properties", parent)
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.setMinimumWidth(200)
        self.setMaximumWidth(340)
        self._build()
        self.show_empty()

    def _build(self):
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background: {THEME['bg_panel']}; border: none; }}"
        )
        self._content = QWidget()
        self._content.setStyleSheet(f"background: {THEME['bg_panel']};")
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(6)
        self._scroll.setWidget(self._content)
        self.setWidget(self._scroll)

    def show_empty(self):
        self._clear()
        lbl = _label("No component selected", muted=True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(lbl)
        self._layout.addStretch()

    def show_component(self, data: dict):
        """Populate with component property fields."""
        self._clear()
        self._layout.addWidget(_section_label("Identity"))
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(6)
        fields = [
            ("Reference", data.get("reference", "")),
            ("Symbol",    data.get("symbol_id", "")),
            ("Standard",  data.get("standard", "")),
            ("Category",  data.get("category", "")),
        ]
        for label, value in fields:
            val_lbl = QLabel(str(value))
            val_lbl.setStyleSheet(f"color: {THEME['text_primary']};")
            form.addRow(_label(label, muted=True), val_lbl)
        self._layout.addLayout(form)

        self._layout.addWidget(_section_label("Position"))
        pos_form = QFormLayout()
        pos_form.setContentsMargins(0, 0, 0, 0)
        pos_form.setSpacing(4)
        pos = data.get("position", {})
        pos_form.addRow(_label("X", muted=True), QLabel(str(pos.get("x", ""))))
        pos_form.addRow(_label("Y", muted=True), QLabel(str(pos.get("y", ""))))
        pos_form.addRow(_label("Rotation", muted=True), QLabel(f"{data.get('rotation', 0)}°"))
        self._layout.addLayout(pos_form)
        self._layout.addStretch()

    def update_selection(self, items: list):
        if not items:
            self.show_empty()
            return
        item = items[0]
        data = item.data(0) if hasattr(item, "data") else {}
        if isinstance(data, dict):
            self.show_component(data)
        else:
            self.show_empty()

    def _clear(self):
        while self._layout.count():
            child = self._layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


# ─────────────────────────────────────────────────────────────────────────────
# MiguelBot Panel (placeholder — full RAG implementation in Phase 3)
# ─────────────────────────────────────────────────────────────────────────────

class MiguelBotPanel(QDockWidget):
    """
    Right dock — MiguelBot AI assistant panel.
    Wired to MiguelBotService via set_service().
    Queries run in a QThread worker — never blocks the UI.
    """

    def __init__(self, canvas=None, parent=None):
        super().__init__("MiguelBot", parent)
        self.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.setMinimumWidth(260)
        self._canvas  = canvas
        self._service = None    # set by mainwindow via set_service()
        self._worker  = None    # active QThread worker (one at a time)
        self._build()

    def _build(self):
        root = QWidget()
        root.setStyleSheet(f"background: {THEME['bg_panel']};")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet(f"background: {THEME['bg_titlebar']}; padding: 6px 10px;")
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(10, 6, 10, 6)
        icon_lbl = QLabel("⚡")
        icon_lbl.setStyleSheet(f"font-size: 14px; color: {THEME['accent_purple']};")
        title_lbl = QLabel("MiguelBot")
        title_lbl.setStyleSheet(f"font-weight: 600; color: {THEME['text_primary']};")
        status_dot = QLabel("●")
        status_dot.setStyleSheet(f"color: {THEME['accent_green']}; font-size: 8px;")
        hlay.addWidget(icon_lbl)
        hlay.addWidget(title_lbl)
        hlay.addStretch()
        hlay.addWidget(status_dot)
        layout.addWidget(header)

        # Context bar
        self._ctx_bar = QLabel("No component selected")
        self._ctx_bar.setStyleSheet(
            f"background: {THEME['bg_titlebar']}; color: {THEME['text_muted']}; "
            f"font-size: 11px; padding: 4px 10px; border-top: 1px solid {THEME['border_main']};"
        )
        layout.addWidget(self._ctx_bar)

        # Chat area
        self._chat = QTextEdit()
        self._chat.setReadOnly(True)
        self._chat.setStyleSheet(
            f"QTextEdit {{ background: {THEME['bg_window']}; color: {THEME['text_primary']}; "
            f"border: none; padding: 10px; font-size: 12px; }}"
        )
        self._chat.setPlaceholderText("MiguelBot will appear here…")
        muted = THEME["text_muted"]
        self._chat.append(
            f'<span style="color:{muted};font-size:11px;">'
            "MiguelBot is ready. Select a component or ask a question.<br>"
            "Connect a MiguelBotService for AI-powered answers.</span>"
        )
        layout.addWidget(self._chat, stretch=1)

        # Quick-action suggestions
        sug_frame = QWidget()
        sug_frame.setStyleSheet(
            f"background: {THEME['bg_panel']}; border-top: 1px solid {THEME['border_main']}; padding: 4px 8px;"
        )
        sug_lay = QVBoxLayout(sug_frame)
        sug_lay.setContentsMargins(6, 4, 6, 4)
        sug_lay.setSpacing(3)
        suggestions = [
            ("Explain ERC errors",         "What ERC errors are on this schematic?"),
            ("Suggest component",          "What component should I use here?"),
            ("How do I wire a motor?",     "How do I wire a 3-phase motor starter?"),
        ]
        for label, query in suggestions:
            btn = QPushButton(label)
            btn.setStyleSheet(
                f"QPushButton {{ background: {THEME['bg_titlebar']}; color: {THEME['accent_blue']}; "
                f"border: 1px solid {THEME['border_main']}; border-radius: 4px; "
                f"padding: 4px 8px; font-size: 11px; text-align: left; }}"
                f"QPushButton:hover {{ background: {THEME['bg_hover']}; }}"
            )
            btn.clicked.connect(lambda checked, q=query: self._submit_query(q))
            sug_lay.addWidget(btn)
        layout.addWidget(sug_frame)

        # Input row
        input_frame = QWidget()
        input_frame.setStyleSheet(
            f"background: {THEME['bg_panel']}; border-top: 1px solid {THEME['border_main']};"
        )
        inp_lay = QHBoxLayout(input_frame)
        inp_lay.setContentsMargins(8, 6, 8, 6)
        inp_lay.setSpacing(6)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Ask MiguelBot…")
        self._input.setStyleSheet(
            f"QLineEdit {{ background: {THEME['bg_hover']}; color: {THEME['text_primary']}; "
            f"border: none; border-radius: 4px; padding: 5px 8px; font-size: 12px; }}"
        )
        self._input.returnPressed.connect(self._on_submit)
        send_btn = QPushButton("→")
        send_btn.setFixedSize(QSize(28, 28))
        send_btn.setStyleSheet(
            f"QPushButton {{ background: {THEME['accent_purple']}; color: white; "
            f"border: none; border-radius: 4px; font-size: 14px; }}"
            f"QPushButton:hover {{ background: #9f97ed; }}"
        )
        send_btn.clicked.connect(self._on_submit)
        inp_lay.addWidget(self._input, stretch=1)
        inp_lay.addWidget(send_btn)
        layout.addWidget(input_frame)

        self.setWidget(root)

    # ── Service wiring ────────────────────────────────────────────────────────

    def set_service(self, service) -> None:
        """
        Connect the MiguelBotService. Called by mainwindow after service.start().
        Updates the status dot colour and welcome message.
        """
        self._service = service
        if service and service.is_ready:
            self._set_status_online(True)
            muted = THEME["text_muted"]
            acc   = THEME["accent_green"]
            self._chat.append(
                f'<span style="color:{acc};font-size:11px;">'
                "✓ MiguelBot connected — RAG pipeline ready.</span>"
            )
        else:
            self._set_status_online(False)

    def _set_status_online(self, online: bool) -> None:
        """Update the green/red dot in the header."""
        colour = THEME["accent_green"] if online else THEME["accent_red"]
        # Find the status dot by walking the header widget
        try:
            header = self.widget().layout().itemAt(0).widget()
            for i in range(header.layout().count()):
                w = header.layout().itemAt(i).widget()
                if w and isinstance(w, QLabel) and "●" in (w.text() or ""):
                    w.setStyleSheet(
                        f"color: {colour}; font-size: 8px;"
                    )
                    break
        except Exception:
            pass

    # ── Context ────────────────────────────────────────────────────────────────

    def update_context(self, items: list):
        if not items:
            self._ctx_bar.setText("No component selected")
        else:
            names = []
            for item in items[:3]:
                data = item.data(0) if hasattr(item, "data") else {}
                if isinstance(data, dict):
                    names.append(data.get("reference", "?"))
            self._ctx_bar.setText(f"Selected: {', '.join(names)}")

    # ── Query submission ──────────────────────────────────────────────────────

    def _on_submit(self):
        query = self._input.text().strip()
        if not query:
            return
        self._input.clear()
        self._submit_query(query)

    def _submit_query(self, query: str) -> None:
        """Submit a query to MiguelBotService in a background QThread."""
        if not query.strip():
            return

        # Show the user's question immediately
        self._chat.append(
            f'<b style="color:{THEME["text_primary"]};">You:</b> {query}'
        )

        if self._service is None:
            self._chat.append(
                f'<span style="color:{THEME["text_muted"]};">'
                "MiguelBot: No service connected. "
                "Call mainwindow.start_miguelbot() to initialise the RAG pipeline.</span><br>"
            )
            return

        # Disable input while answering
        self._input.setEnabled(False)
        self._chat.append(
            f'<span style="color:{THEME["text_muted"]};font-style:italic;">Thinking…</span>'
        )

        # Build schematic context snapshot
        ctx = {}
        if self._canvas:
            try:
                ctx = self._canvas.get_context_snapshot()
            except Exception:
                pass

        # Run in background thread so UI stays responsive
        from PyQt6.QtCore import QThread, pyqtSignal as Signal, QObject

        class _Worker(QObject):
            finished = Signal(object)   # emits RAGAnswer
            error    = Signal(str)

            def __init__(self, service, q, context):
                super().__init__()
                self._service = service
                self._q       = q
                self._context = context

            def run(self):
                try:
                    answer = self._service.ask(self._q, self._context)
                    self.finished.emit(answer)
                except Exception as exc:
                    self.error.emit(str(exc))

        # Cancel any previous worker
        if self._worker is not None:
            try:
                self._worker.quit()
                self._worker.wait(200)
            except Exception:
                pass

        thread = QThread(self)
        worker = _Worker(self._service, query, ctx)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda ans: self._on_answer(ans, thread))
        worker.error.connect(lambda e: self._on_error(e, thread))
        self._worker = thread
        thread.start()

    def _on_answer(self, answer, thread: "QThread") -> None:
        """Called in main thread when worker finishes."""
        self._input.setEnabled(True)

        # Remove the "Thinking…" placeholder (last paragraph)
        cursor = self._chat.textCursor()
        from PyQt6.QtGui import QTextCursor
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        cursor.removeSelectedText()

        acc  = THEME["accent_purple"]
        muted = THEME["text_muted"]
        self._chat.append(
            f'<b style="color:{acc};">⚡ MiguelBot:</b> {answer.answer}'
        )

        # Show sources if available
        if answer.sources:
            src_labels = []
            for chunk in answer.sources[:3]:
                src = (chunk.metadata.get("source_file")
                       or chunk.metadata.get("symbol_id")
                       or chunk.collection)
                if src:
                    src_labels.append(src)
            if src_labels:
                self._chat.append(
                    f'<span style="color:{muted};font-size:10px;">'
                    f"Sources: {', '.join(src_labels)}</span>"
                )

        # Escalation notice
        if answer.should_escalate:
            self._chat.append(
                f'<span style="color:{muted};font-size:10px;font-style:italic;">'
                "Low confidence — consider posting to GitHub Discussions for expert help.</span>"
            )

        self._chat.append("")
        self._scroll_to_bottom()

        try:
            thread.quit()
            thread.wait(200)
        except Exception:
            pass

    def _on_error(self, error_msg: str, thread: "QThread") -> None:
        self._input.setEnabled(True)
        self._chat.append(
            f'<span style="color:{THEME["accent_red"]};">'
            f"Error: {error_msg}</span><br>"
        )
        self._scroll_to_bottom()
        try:
            thread.quit()
            thread.wait(200)
        except Exception:
            pass

    def _scroll_to_bottom(self) -> None:
        sb = self._chat.verticalScrollBar()
        sb.setValue(sb.maximum())
