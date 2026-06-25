"""
miguel_angel — Main Window
Frontend Developer implementation · Phase 3

MiguelAngelMainWindow orchestrates:
  - MiguelAngelMenuBar   (8 menus)
  - CanvasToolbar        (vertical tool palette)
  - SchematicCanvas      (QGraphicsView infinite canvas)
  - ProjectNavigatorPanel (left dock)
  - ComponentLibraryPanel (right dock)
  - PropertiesPanel       (right dock, tabbed)
  - MiguelBotPanel        (right dock, toggle F1)
  - QStatusBar            (zoom · coordinates · ERC status)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QApplication,
    QDockWidget, QStatusBar, QLabel,
    QMessageBox, QFileDialog, QTabWidget,
)
from PyQt6.QtCore  import Qt, QSettings, QSize, QPoint
from PyQt6.QtGui   import QCloseEvent, QKeySequence, QShortcut

from .constants    import (
    APP_NAME, APP_VERSION, APP_DESCRIPTION, APP_URL, APP_LICENSE, APP_AUTHOR,
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT,
    STYLESHEET, THEME,
)
from .menubar  import MiguelAngelMenuBar
from .toolbar  import CanvasToolbar
from .canvas   import SchematicCanvas
from miguel_angel.miguelbot import MiguelBotService
from .panels   import (
    ProjectNavigatorPanel,
    ComponentLibraryPanel,
    PropertiesPanel,
    MiguelBotPanel,
)


class MiguelAngelMainWindow(QMainWindow):
    """
    Top-level application window.
    Owns all child widgets and wires their signals together.
    """

    def __init__(self, library_db=None):
        super().__init__()
        self._library_db  = library_db
        self._current_file: Optional[Path] = None
        self._unsaved_changes = False

        self._init_ui()
        self._connect_signals()
        self._restore_geometry()
        self._update_title()

    # ── UI construction ───────────────────────────────────────────────────────

    def _init_ui(self):
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.setWindowTitle(APP_NAME)
        self.setStyleSheet(STYLESHEET)
        self._bot_service = None   # set by start_miguelbot()
        self._bot_thread  = None

        # ── Menu bar
        self._menubar = MiguelAngelMenuBar(self)
        self.setMenuBar(self._menubar)

        # ── Canvas (central widget)
        self._canvas = SchematicCanvas(self)
        self.setCentralWidget(self._canvas)

        # ── Toolbar (vertical, left of canvas)
        self._toolbar = CanvasToolbar(self)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self._toolbar)

        # ── Status bar
        self._status_bar = QStatusBar(self)
        self.setStatusBar(self._status_bar)

        self._lbl_tool   = QLabel("Select")
        self._lbl_coords = QLabel("x: 0  y: 0")
        self._lbl_zoom   = QLabel("100%")
        self._lbl_erc    = QLabel("ERC: —")
        self._lbl_file   = QLabel("No project")

        for lbl in [self._lbl_tool, self._lbl_coords, self._lbl_zoom, self._lbl_erc]:
            lbl.setStyleSheet(f"color: {THEME['text_muted']}; padding: 0 10px;")
            self._status_bar.addWidget(lbl)
        self._lbl_file.setStyleSheet(f"color: {THEME['text_muted']}; padding: 0 10px;")
        self._status_bar.addPermanentWidget(self._lbl_file)

        # ── Dock panels
        self._dock_nav  = ProjectNavigatorPanel(self)
        self._dock_lib  = ComponentLibraryPanel(self._library_db, self)
        self._dock_prop = PropertiesPanel(self)
        self._dock_bot  = MiguelBotPanel(self._canvas, self)

        # Left dock: project navigator
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._dock_nav)

        # Right dock: library + properties (tabbed), MiguelBot (hidden by default)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._dock_lib)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._dock_prop)
        self.tabifyDockWidget(self._dock_lib, self._dock_prop)
        self._dock_lib.raise_()

        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._dock_bot)
        self._dock_bot.hide()

        self.setDockNestingEnabled(True)

        # F1 shortcut for MiguelBot
        f1 = QShortcut(QKeySequence("F1"), self)
        f1.activated.connect(self._toggle_miguelbot)

    # ── Signal wiring ─────────────────────────────────────────────────────────

    def _connect_signals(self):
        mb = self._menubar

        # File menu
        mb.act_new.triggered.connect(self.new_project)
        mb.act_open.triggered.connect(self.open_project)
        mb.act_save.triggered.connect(self.save_project)
        mb.act_save_as.triggered.connect(self.save_project_as)
        mb.act_exit.triggered.connect(self.close)

        # Export menu
        mb.act_export_pdf.triggered.connect(lambda: self._export("pdf"))
        mb.act_export_dxf.triggered.connect(lambda: self._export("dxf"))
        mb.act_export_svg.triggered.connect(lambda: self._export("svg"))
        mb.act_export_kicad.triggered.connect(lambda: self._export("kicad"))

        # Edit menu
        mb.act_undo.triggered.connect(self._on_undo)
        mb.act_redo.triggered.connect(self._on_redo)
        mb.act_select_all.triggered.connect(
            lambda: self._canvas._scene.selectAll()
        )
        mb.act_delete.triggered.connect(self._on_delete)
        mb.act_prefs.triggered.connect(self._show_preferences)

        # View menu
        mb.act_zoom_in.triggered.connect(self._canvas.zoom_in)
        mb.act_zoom_out.triggered.connect(self._canvas.zoom_out)
        mb.act_zoom_fit.triggered.connect(self._canvas.zoom_fit)
        mb.act_zoom_100.triggered.connect(self._canvas.zoom_100)
        mb.act_toggle_grid.triggered.connect(
            lambda checked: self._canvas.set_grid_visible(checked)
        )
        mb.act_toggle_snap.triggered.connect(
            lambda checked: self._canvas.set_snap_enabled(checked)
        )
        mb.act_toggle_bot.triggered.connect(self._toggle_miguelbot)
        mb.act_toggle_lib.triggered.connect(
            lambda c: self._dock_lib.show() if c else self._dock_lib.hide()
        )
        mb.act_toggle_prop.triggered.connect(
            lambda c: self._dock_prop.show() if c else self._dock_prop.hide()
        )
        mb.act_toggle_nav.triggered.connect(
            lambda c: self._dock_nav.show() if c else self._dock_nav.hide()
        )
        mb.act_reset_layout.triggered.connect(self._reset_layout)

        # Tools menu
        mb.act_erc.triggered.connect(self._run_erc)
        mb.act_bom.triggered.connect(self._generate_bom)

        # Help menu
        mb.act_about.triggered.connect(self._show_about)
        mb.act_docs.triggered.connect(self._open_docs)
        mb.act_migbot.triggered.connect(self._toggle_miguelbot)

        # Toolbar
        self._toolbar.tool_changed.connect(self._on_tool_changed)
        self._toolbar.act_zoom_in.triggered.connect(self._canvas.zoom_in)
        self._toolbar.act_zoom_out.triggered.connect(self._canvas.zoom_out)

        # Canvas
        self._canvas.selection_changed.connect(self._on_selection_changed)
        self._canvas.coordinates_changed.connect(self._on_coords_changed)
        self._canvas.erc_results_changed.connect(self._on_erc_results)

        # Component library
        self._dock_lib.symbol_selected.connect(self._on_symbol_selected)

        # Navigator
        self._dock_nav.sheet_selected.connect(self._on_sheet_selected)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_tool_changed(self, tool: str):
        self._canvas.set_tool(tool)
        self._lbl_tool.setText(tool.title())

    def _on_selection_changed(self, items: list):
        self._dock_prop.update_selection(items)
        self._dock_bot.update_context(items)

    def _on_coords_changed(self, x: float, y: float):
        self._lbl_coords.setText(f"x: {x:.1f}  y: {y:.1f}")

    def _on_erc_results(self, violations: list):
        count = len(violations)
        if count == 0:
            self._lbl_erc.setText("ERC: ✓")
            self._lbl_erc.setStyleSheet(
                f"color: {THEME['accent_green']}; padding: 0 10px;"
            )
        else:
            self._lbl_erc.setText(f"ERC: {count} issue{'s' if count != 1 else ''}")
            self._lbl_erc.setStyleSheet(
                f"color: {THEME['accent_red']}; padding: 0 10px;"
            )

    def _on_symbol_selected(self, symbol_id: str):
        """
        Called when user double-clicks a symbol in the library browser.
        Fetches symbol geometry/pin data and arms the canvas for placement.
        """
        symbol_data = {"width_lu": 4.0, "height_lu": 4.0, "pins": [], "reference_prefix": "X"}

        if self._library_db:
            try:
                sym = self._library_db.get_symbol(symbol_id)
                if sym:
                    symbol_data = {
                        "width_lu":        sym.width,
                        "height_lu":       sym.height,
                        "reference_prefix": sym.reference_prefix,
                        "pins": [
                            {
                                "pin_number": p.pin_number,
                                "name":       p.name,
                                "pin_type":   p.pin_type,
                                "x_offset":   p.x_offset,
                                "y_offset":   p.y_offset,
                                "orientation": p.orientation,
                            }
                            for p in sym.pins
                        ],
                    }
            except Exception as exc:
                import logging
                logging.getLogger("miguel_angel.mainwindow").warning(
                    "Could not load symbol %s: %s", symbol_id, exc
                )

        self._canvas.set_pending_symbol(symbol_id, symbol_data)
        self.statusBar().showMessage(
            f"Placing {symbol_id}  —  click canvas to place  |  Esc to cancel", 0
        )

    def start_miguelbot(self, docs_path=None) -> None:
        """
        Initialise and start MiguelBotService in a background QThread.
        Called on application startup (non-blocking).
        """
        from PyQt6.QtCore import QThread

        class _StartWorker(QThread):
            def __init__(self, service):
                super().__init__()
                self._service = service
            def run(self):
                try:
                    self._service.start()
                except Exception as exc:
                    import logging
                    logging.getLogger("miguel_angel.mainwindow").warning(
                        "MiguelBot start failed: %s", exc
                    )

        from pathlib import Path
        from miguel_angel.miguelbot import EmbeddingBackend
        svc = MiguelBotService(
            docs_path    = docs_path or Path("docs/"),
            library_db   = self._library_db,
            in_memory    = False,
        )
        self._bot_service = svc

        worker = _StartWorker(svc)
        worker.finished.connect(lambda: self._dock_bot.set_service(svc))
        worker.start()
        self._bot_thread = worker   # keep reference

    def _on_sheet_selected(self, sheet_name: str):
        self.statusBar().showMessage(f"Switched to: {sheet_name}", 2000)

    def _toggle_miguelbot(self):
        if self._dock_bot.isVisible():
            self._dock_bot.hide()
            self._menubar.act_toggle_bot.setChecked(False)
        else:
            self._dock_bot.show()
            self._dock_bot.raise_()
            self._menubar.act_toggle_bot.setChecked(True)

    def _reset_layout(self):
        self._dock_nav.show()
        self._dock_lib.show()
        self._dock_prop.show()
        self._dock_bot.hide()

    # ── File operations ───────────────────────────────────────────────────────

    def new_project(self):
        if self._unsaved_changes and not self._confirm_discard():
            return
        self._current_file    = None
        self._unsaved_changes = False
        self._canvas._scene.clear()
        self._canvas._draw_grid()
        self._dock_nav.load_project(None)
        self._update_title()
        self.statusBar().showMessage("New project created", 2000)

    def open_project(self):
        if self._unsaved_changes and not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open project", "",
            "miguel_angel project (*.maproj);;All files (*)"
        )
        if not path:
            return
        try:
            from miguel_angel.core import MAprojIO
            io      = MAprojIO()
            project = io.load(Path(path))
            self._current_file    = Path(path)
            self._unsaved_changes = False
            self._canvas.project_loaded.emit()
            self._dock_nav.load_project(project)
            self._update_title()
            self.statusBar().showMessage(f"Opened: {Path(path).name}", 3000)
        except Exception as exc:
            QMessageBox.critical(self, "Open failed", str(exc))

    def save_project(self):
        if not self._current_file:
            self.save_project_as()
            return
        self._do_save(self._current_file)

    def save_project_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save project as", "",
            "miguel_angel project (*.maproj);;All files (*)"
        )
        if path:
            if not path.endswith(".maproj"):
                path += ".maproj"
            self._do_save(Path(path))

    def _do_save(self, path: Path):
        try:
            from miguel_angel.core import MAprojIO, Project, ProjectMetadata, Sheet
            # Minimal save — full model persistence in Phase 3
            proj = Project(
                metadata=ProjectMetadata(name=path.stem),
                sheets=[Sheet(name="Sheet 1")]
            )
            MAprojIO().save(proj, path)
            self._current_file    = path
            self._unsaved_changes = False
            self._update_title()
            self.statusBar().showMessage(f"Saved: {path.name}", 2000)
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))

    def _confirm_discard(self) -> bool:
        reply = QMessageBox.question(
            self, "Unsaved changes",
            "You have unsaved changes. Discard them?",
            QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
        )
        return reply == QMessageBox.StandardButton.Discard

    def _export(self, fmt: str):
        QMessageBox.information(
            self, "Export",
            f"Export to {fmt.upper()} will be available once the export engine "
            f"is implemented by the Backend Developer in Phase 4."
        )

    # ── Edit operations ───────────────────────────────────────────────────────

    def _on_undo(self):
        self.statusBar().showMessage("Undo — history engine Phase 4", 1500)

    def _on_redo(self):
        self.statusBar().showMessage("Redo — history engine Phase 4", 1500)

    def _on_delete(self):
        for item in self._canvas._scene.selectedItems():
            self._canvas._scene.removeItem(item)
        self._unsaved_changes = True

    # ── Tools ─────────────────────────────────────────────────────────────────

    def _run_erc(self):
        self.statusBar().showMessage(
            "ERC requires a loaded project. Open a .maproj file first.", 3000
        )

    def _generate_bom(self):
        QMessageBox.information(
            self, "BOM",
            "Bill of Materials generation will be available in Phase 4 "
            "(Data Scientist — BOM generator)."
        )

    # ── Dialogs ───────────────────────────────────────────────────────────────

    def _show_about(self):
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"<h3>{APP_NAME} {APP_VERSION}</h3>"
            f"<p>{APP_DESCRIPTION}</p>"
            f"<p>License: {APP_LICENSE}</p>"
            f"<p>Author: {APP_AUTHOR}</p>"
            f"<p><a href='{APP_URL}'>{APP_URL}</a></p>"
            f"<p>Developed with assistance from Anthropic Claude.</p>"
        )

    def _open_docs(self):
        import webbrowser
        webbrowser.open(f"{APP_URL}/tree/main/docs")

    def _show_preferences(self):
        QMessageBox.information(
            self, "Preferences",
            "Preferences panel — coming in Phase 3."
        )

    # ── Title + geometry ──────────────────────────────────────────────────────

    def _update_title(self):
        unsaved  = "• " if self._unsaved_changes else ""
        filename = self._current_file.name if self._current_file else "New project"
        self.setWindowTitle(f"{unsaved}{filename} — {APP_NAME} {APP_VERSION}")
        self._lbl_file.setText(
            self._current_file.name if self._current_file else "No project"
        )

    def _save_geometry(self):
        s = QSettings(APP_NAME, APP_NAME)
        s.setValue("geometry", self.saveGeometry())
        s.setValue("windowState", self.saveState())

    def _restore_geometry(self):
        s = QSettings(APP_NAME, APP_NAME)
        geom = s.value("geometry")
        state = s.value("windowState")
        if geom:
            self.restoreGeometry(geom)
        else:
            self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)
            self.move(100, 60)
        if state:
            self.restoreState(state)

    def closeEvent(self, event: QCloseEvent):
        if self._unsaved_changes:
            reply = QMessageBox.question(
                self, "Quit",
                "You have unsaved changes. Quit anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        self._save_geometry()
        event.accept()
