"""
miguel_angel — Component Library Database Engine
Database Specialist implementation · Phase 2

Manages the SQLite component library:
  - LibraryDB.connect()         → open / create the database
  - LibraryDB.create_schema()   → create all tables via SQLAlchemy
  - LibraryDB.seed_standards()  → insert ISA/IEC/ANSI/IEEE seed data
  - LibraryDB.seed_symbols()    → insert representative symbol set
  - LibraryDB.search()          → full-text symbol search
  - LibraryDB.get_symbol()      → fetch by symbol_id
  - LibraryDB.stats()           → count symbols per standard
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, func, or_, select, text
from sqlalchemy.orm import Session, sessionmaker

from .library_models import (
    Base, Standard, Category, Symbol, SymbolPin,
    SymbolKeyword, SymbolAlias, LineType, Manufacturer,
)

logger = logging.getLogger("miguel_angel.library_db")

LIBRARY_DB_FILENAME = "library.db"


def _get_library_db_path() -> Path:
    import os
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    elif hasattr(os, "uname") and os.uname().sysname == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / "miguel_angel"
    path.mkdir(parents=True, exist_ok=True)
    return path / LIBRARY_DB_FILENAME


class LibraryDB:
    """
    Component library database manager.

    Usage:
        db = LibraryDB()
        db.connect()
        results = db.search("temperature controller")
        symbol  = db.get_symbol("ISA51:TIC")
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or _get_library_db_path()
        self._engine = None
        self._Session = None

    # ── Connection ────────────────────────────────────────────────────────────

    def connect(self, seed: bool = True) -> None:
        """Open the database. Creates schema and seeds data on first run."""
        url = f"sqlite:///{self.db_path}"
        self._engine = create_engine(url, echo=False, future=True)
        self._Session = sessionmaker(bind=self._engine, expire_on_commit=False)

        # Enable WAL mode for better concurrent read performance
        with self._engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA foreign_keys=ON"))
            conn.commit()

        self.create_schema()
        if seed:
            self._seed_if_empty()
        logger.info("Library DB connected: %s", self.db_path)

    def session(self) -> Session:
        if self._Session is None:
            raise RuntimeError("Call connect() first.")
        return self._Session()

    def create_schema(self) -> None:
        """Create all tables (idempotent — safe to call multiple times)."""
        Base.metadata.create_all(self._engine)
        logger.debug("Schema created/verified")

    def close(self) -> None:
        if self._engine:
            self._engine.dispose()

    # ── Seed ──────────────────────────────────────────────────────────────────

    def _seed_if_empty(self) -> None:
        with self.session() as s:
            count = s.execute(select(func.count(Standard.id))).scalar_one()
        if count == 0:
            logger.info("Empty library — seeding standards and symbols")
            self.seed_standards()
            self.seed_line_types()
            self.seed_symbols()

    def seed_standards(self) -> None:
        """Insert the 7 supported standards + Custom."""
        standards = [
            dict(code="ISA 5.1",   name="Instrumentation Symbols and Identification",
                 organisation="ISA", region="International",
                 scope="P&ID symbols for instrumentation and control: indicators, controllers, transmitters, valves, switches"),
            dict(code="ISA 5.2",   name="Binary Logic Diagrams for Process Operations",
                 organisation="ISA", region="International",
                 scope="Logic gate symbols for interlocks, AND/OR/NOT gates, timers, counters"),
            dict(code="ISA 5.4",   name="Instrument Loop Diagrams",
                 organisation="ISA", region="International",
                 scope="Loop diagram symbols: transmitters, controllers, final elements, signal converters"),
            dict(code="ISA 95",    name="Enterprise-Control System Integration",
                 organisation="ISA", region="International",
                 scope="Automation hierarchy: Levels 0-4, PLC, DCS, SCADA, MES, ERP integration symbols"),
            dict(code="IEC 60617", name="Graphical Symbols for Diagrams",
                 organisation="IEC", region="International",
                 scope="Electrical diagram symbols: switchgear, protection, machines, transformers, power electronics"),
            dict(code="ANSI/NEMA", name="North American Electrical Standards",
                 organisation="NEMA", region="North America",
                 scope="US/Canada electrical symbols: contactors, relays, push buttons, motor starters, fuses"),
            dict(code="IEEE 315",  name="Graphic Symbols for Electrical and Electronics Diagrams",
                 organisation="IEEE", region="International",
                 scope="Electronic symbols: passive components, semiconductors, logic gates, ICs, connectors"),
            dict(code="Custom",    name="User-Defined Symbols",
                 organisation="User", region="Local",
                 scope="Company-specific or user-created symbols not covered by standard libraries"),
        ]
        with self.session() as s:
            for data in standards:
                if not s.execute(select(Standard).where(Standard.code == data["code"])).scalar_one_or_none():
                    s.add(Standard(**data))
            s.commit()
        logger.info("Seeded %d standards", len(standards))

    def seed_line_types(self) -> None:
        """Insert ISA 5.1 signal lines and IEC 60617 power lines."""
        with self.session() as s:
            isa = s.execute(select(Standard).where(Standard.code == "ISA 5.1")).scalar_one()
            iec = s.execute(select(Standard).where(Standard.code == "IEC 60617")).scalar_one()

        line_types = [
            # ISA 5.1 signal lines
            dict(standard_id=isa.id, code="ISA51_PROCESS",   name="Process connection",
                 description="Main process line — solid", dash_pattern=None, line_weight=1.5, color_hex="#000000"),
            dict(standard_id=isa.id, code="ISA51_PNEUMATIC",  name="Pneumatic signal",
                 description="Pneumatic instrument signal — dashed", dash_pattern="8,4", line_weight=1.0, color_hex="#000000"),
            dict(standard_id=isa.id, code="ISA51_ELECTRIC",   name="Electric signal",
                 description="Electric instrument signal — dotted", dash_pattern="2,4", line_weight=1.0, color_hex="#000000"),
            dict(standard_id=isa.id, code="ISA51_HYDRAULIC",  name="Hydraulic signal",
                 description="Hydraulic instrument signal — dash-dot", dash_pattern="8,4,2,4", line_weight=1.0, color_hex="#000000"),
            dict(standard_id=isa.id, code="ISA51_CAPILLARY",  name="Capillary",
                 description="Capillary tubing connection — long dash", dash_pattern="16,4", line_weight=1.0, color_hex="#000000"),
            dict(standard_id=isa.id, code="ISA51_GUIDEDWAVE", name="Guided wave / fiber optic",
                 description="Fiber optic or guided wave signal", dash_pattern="4,2,4,2,2,2", line_weight=1.0, color_hex="#000000"),
            # IEC 60617 power lines
            dict(standard_id=iec.id, code="IEC_HV",           name="High voltage conductor",
                 description="High voltage power — bold solid", dash_pattern=None, line_weight=3.0, color_hex="#000000"),
            dict(standard_id=iec.id, code="IEC_CONTROL",      name="Control wire",
                 description="Control circuit wiring — thin solid", dash_pattern=None, line_weight=1.0, color_hex="#000000"),
            dict(standard_id=iec.id, code="IEC_GROUND_PE",    name="Ground / protective earth",
                 description="Protective earth conductor", dash_pattern=None, line_weight=1.5, color_hex="#00AA00"),
            dict(standard_id=iec.id, code="IEC_BUS",          name="Bus bar",
                 description="Electrical bus bar — very bold", dash_pattern=None, line_weight=4.0, color_hex="#000000"),
            dict(standard_id=iec.id, code="IEC_NEUTRAL",      name="Neutral conductor",
                 description="Neutral wire (N)", dash_pattern=None, line_weight=1.5, color_hex="#0000AA"),
        ]
        with self.session() as s:
            for data in line_types:
                existing = s.execute(select(LineType).where(LineType.code == data["code"])).scalar_one_or_none()
                if not existing:
                    s.add(LineType(**data))
            s.commit()
        logger.info("Seeded %d line types", len(line_types))

    def seed_symbols(self) -> None:  # noqa: C901
        """Seed representative symbol set for all 7 standards."""
        with self.session() as s:
            stds = {r.code: r for r in s.execute(select(Standard)).scalars()}

        # Helper to add category if not existing
        def get_or_create_cat(session: Session, std_id: int, code: str, name: str, sort: int = 0) -> int:
            cat = session.execute(
                select(Category).where(Category.standard_id == std_id, Category.code == code)
            ).scalar_one_or_none()
            if not cat:
                cat = Category(standard_id=std_id, code=code, name=name, sort_order=sort)
                session.add(cat)
                session.flush()
            return cat.id

        # Helper to add symbol + pins + keywords
        def add_symbol(session: Session, data: dict, pins: list[dict], kws: list[str], aliases: list[dict] | None = None) -> None:
            existing = session.execute(
                select(Symbol).where(Symbol.symbol_id == data["symbol_id"])
            ).scalar_one_or_none()
            if existing:
                return
            sym = Symbol(**data)
            session.add(sym)
            session.flush()
            for p in pins:
                session.add(SymbolPin(symbol_id=sym.id, **p))
            for kw in kws:
                session.add(SymbolKeyword(symbol_id=sym.id, keyword=kw.lower()))
            for al in (aliases or []):
                session.add(SymbolAlias(symbol_id=sym.id, **al))

        with self.session() as s:

            # ── ISA 5.1 ──────────────────────────────────────────────────────
            isa51_id = stds["ISA 5.1"].id
            cat_ind  = get_or_create_cat(s, isa51_id, "IND",  "Indicators",  1)
            cat_ctrl = get_or_create_cat(s, isa51_id, "CTRL", "Controllers", 2)
            cat_trns = get_or_create_cat(s, isa51_id, "TRNS", "Transmitters",3)
            cat_valv = get_or_create_cat(s, isa51_id, "VALV", "Valves",      4)
            cat_sw   = get_or_create_cat(s, isa51_id, "SW",   "Switches",    5)

            _isa51_symbols = [
                (dict(symbol_id="ISA51:TI",  standard_id=isa51_id, category_id=cat_ind,  name="Temperature indicator",
                      reference_prefix="TI",  isa_tag="TI",  measured_variable="T", function_letters="I",
                      description="ISA 5.1 temperature indicator — field mounted, locally readable"),
                 [dict(pin_number="1", name="IN",  pin_type="Signal",  x_offset=-2.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="2", name="PWR", pin_type="Power",   x_offset=0.0,  y_offset=2.0, orientation="N")],
                 ["temperature", "indicator", "TI", "field", "local", "ISA51"]),

                (dict(symbol_id="ISA51:TIC", standard_id=isa51_id, category_id=cat_ctrl, name="Temperature indicator controller",
                      reference_prefix="TIC", isa_tag="TIC", measured_variable="T", function_letters="IC",
                      description="ISA 5.1 temperature indicator controller — panel mounted with local indication"),
                 [dict(pin_number="1", name="PV",  pin_type="Input",  x_offset=-2.0, y_offset=0.0,  orientation="W"),
                  dict(pin_number="2", name="OUT", pin_type="Output", x_offset=2.0,  y_offset=0.0,  orientation="E"),
                  dict(pin_number="3", name="PWR", pin_type="Power",  x_offset=0.0,  y_offset=2.0,  orientation="N"),
                  dict(pin_number="4", name="GND", pin_type="Ground", x_offset=0.0,  y_offset=-2.0, orientation="S")],
                 ["temperature", "indicator", "controller", "TIC", "PID", "ISA51"],
                 [dict(alias="TC",  alias_type="ansi"), dict(alias="Temperature Controller", alias_type="name")]),

                (dict(symbol_id="ISA51:PI",  standard_id=isa51_id, category_id=cat_ind,  name="Pressure indicator",
                      reference_prefix="PI",  isa_tag="PI",  measured_variable="P", function_letters="I",
                      description="ISA 5.1 pressure indicator — local reading"),
                 [dict(pin_number="1", name="IN",  pin_type="Signal", x_offset=-2.0, y_offset=0.0, orientation="W")],
                 ["pressure", "indicator", "PI", "gauge", "ISA51"]),

                (dict(symbol_id="ISA51:PIC", standard_id=isa51_id, category_id=cat_ctrl, name="Pressure indicator controller",
                      reference_prefix="PIC", isa_tag="PIC", measured_variable="P", function_letters="IC",
                      description="ISA 5.1 pressure indicator controller"),
                 [dict(pin_number="1", name="PV",  pin_type="Input",  x_offset=-2.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="2", name="OUT", pin_type="Output", x_offset=2.0,  y_offset=0.0, orientation="E"),
                  dict(pin_number="3", name="PWR", pin_type="Power",  x_offset=0.0,  y_offset=2.0, orientation="N")],
                 ["pressure", "controller", "PIC", "ISA51"]),

                (dict(symbol_id="ISA51:FI",  standard_id=isa51_id, category_id=cat_ind,  name="Flow indicator",
                      reference_prefix="FI",  isa_tag="FI",  measured_variable="F", function_letters="I",
                      description="ISA 5.1 flow indicator"),
                 [dict(pin_number="1", name="IN",  pin_type="Signal", x_offset=-2.0, y_offset=0.0, orientation="W")],
                 ["flow", "indicator", "FI", "ISA51"]),

                (dict(symbol_id="ISA51:FIC", standard_id=isa51_id, category_id=cat_ctrl, name="Flow indicator controller",
                      reference_prefix="FIC", isa_tag="FIC", measured_variable="F", function_letters="IC",
                      description="ISA 5.1 flow indicator controller"),
                 [dict(pin_number="1", name="PV",  pin_type="Input",  x_offset=-2.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="2", name="OUT", pin_type="Output", x_offset=2.0,  y_offset=0.0, orientation="E"),
                  dict(pin_number="3", name="PWR", pin_type="Power",  x_offset=0.0,  y_offset=2.0, orientation="N")],
                 ["flow", "controller", "FIC", "ISA51"]),

                (dict(symbol_id="ISA51:LI",  standard_id=isa51_id, category_id=cat_ind,  name="Level indicator",
                      reference_prefix="LI",  isa_tag="LI",  measured_variable="L", function_letters="I",
                      description="ISA 5.1 level indicator"),
                 [dict(pin_number="1", name="IN",  pin_type="Signal", x_offset=-2.0, y_offset=0.0, orientation="W")],
                 ["level", "indicator", "LI", "ISA51"]),

                (dict(symbol_id="ISA51:FCV", standard_id=isa51_id, category_id=cat_valv, name="Flow control valve",
                      reference_prefix="FCV", isa_tag="FCV", measured_variable="F", function_letters="CV",
                      description="ISA 5.1 flow control valve — modulating", width=6.0),
                 [dict(pin_number="1", name="IN",   pin_type="Passive", x_offset=-3.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="2", name="OUT",  pin_type="Passive", x_offset=3.0,  y_offset=0.0, orientation="E"),
                  dict(pin_number="3", name="CTRL", pin_type="Input",   x_offset=0.0,  y_offset=2.0, orientation="N")],
                 ["valve", "control", "FCV", "modulating", "ISA51"]),

                (dict(symbol_id="ISA51:PSV", standard_id=isa51_id, category_id=cat_valv, name="Pressure safety valve",
                      reference_prefix="PSV", isa_tag="PSV", measured_variable="P", function_letters="SV",
                      description="ISA 5.1 pressure safety valve — relief", width=6.0),
                 [dict(pin_number="1", name="IN",  pin_type="Passive", x_offset=-3.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="2", name="OUT", pin_type="Passive", x_offset=3.0,  y_offset=0.0, orientation="E")],
                 ["pressure", "safety", "valve", "relief", "PSV", "ISA51"]),

                (dict(symbol_id="ISA51:TE",  standard_id=isa51_id, category_id=cat_trns, name="Temperature element / sensor",
                      reference_prefix="TE",  isa_tag="TE",  measured_variable="T", function_letters="E",
                      description="ISA 5.1 temperature element — thermocouple or RTD in process"),
                 [dict(pin_number="1", name="+",   pin_type="Output", x_offset=-2.0, y_offset=0.5,  orientation="W"),
                  dict(pin_number="2", name="-",   pin_type="Output", x_offset=-2.0, y_offset=-0.5, orientation="W")],
                 ["temperature", "element", "thermocouple", "RTD", "sensor", "TE", "ISA51"]),

                (dict(symbol_id="ISA51:TT",  standard_id=isa51_id, category_id=cat_trns, name="Temperature transmitter",
                      reference_prefix="TT",  isa_tag="TT",  measured_variable="T", function_letters="T",
                      description="ISA 5.1 temperature transmitter — 4-20mA output"),
                 [dict(pin_number="1", name="IN",  pin_type="Input",  x_offset=-2.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="2", name="OUT", pin_type="Output", x_offset=2.0,  y_offset=0.0, orientation="E"),
                  dict(pin_number="3", name="+24", pin_type="Power",  x_offset=0.0,  y_offset=2.0, orientation="N")],
                 ["temperature", "transmitter", "4-20mA", "TT", "ISA51"]),

                (dict(symbol_id="ISA51:HS",  standard_id=isa51_id, category_id=cat_sw, name="Hand switch",
                      reference_prefix="HS",  isa_tag="HS",  measured_variable="H", function_letters="S",
                      description="ISA 5.1 hand-operated selector/push-button switch"),
                 [dict(pin_number="1", name="COM", pin_type="Passive", x_offset=-2.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="2", name="NO",  pin_type="Passive", x_offset=2.0,  y_offset=0.5, orientation="E"),
                  dict(pin_number="3", name="NC",  pin_type="Passive", x_offset=2.0,  y_offset=-0.5, orientation="E")],
                 ["hand", "switch", "selector", "HS", "operator", "ISA51"]),
            ]
            for sym_data, pins, kws, *rest in _isa51_symbols:
                add_symbol(s, sym_data, pins, kws, rest[0] if rest else None)

            # ── ISA 5.2 ──────────────────────────────────────────────────────
            isa52_id = stds["ISA 5.2"].id
            cat_gate = get_or_create_cat(s, isa52_id, "GATE", "Logic Gates", 1)
            cat_lock = get_or_create_cat(s, isa52_id, "LOCK", "Interlocks",  2)

            _isa52 = [
                (dict(symbol_id="ISA52:AND", standard_id=isa52_id, category_id=cat_gate,
                      name="AND gate", reference_prefix="AND", description="ISA 5.2 AND logic element"),
                 [dict(pin_number="1", name="A",   pin_type="Input",  x_offset=-2.0, y_offset=0.5,  orientation="W"),
                  dict(pin_number="2", name="B",   pin_type="Input",  x_offset=-2.0, y_offset=-0.5, orientation="W"),
                  dict(pin_number="3", name="OUT", pin_type="Output", x_offset=2.0,  y_offset=0.0,  orientation="E")],
                 ["AND", "gate", "logic", "interlock", "ISA52"]),

                (dict(symbol_id="ISA52:OR",  standard_id=isa52_id, category_id=cat_gate,
                      name="OR gate",  reference_prefix="OR",  description="ISA 5.2 OR logic element"),
                 [dict(pin_number="1", name="A",   pin_type="Input",  x_offset=-2.0, y_offset=0.5,  orientation="W"),
                  dict(pin_number="2", name="B",   pin_type="Input",  x_offset=-2.0, y_offset=-0.5, orientation="W"),
                  dict(pin_number="3", name="OUT", pin_type="Output", x_offset=2.0,  y_offset=0.0,  orientation="E")],
                 ["OR", "gate", "logic", "ISA52"]),

                (dict(symbol_id="ISA52:NOT", standard_id=isa52_id, category_id=cat_gate,
                      name="NOT gate / inverter", reference_prefix="NOT", description="ISA 5.2 NOT / invert element"),
                 [dict(pin_number="1", name="IN",  pin_type="Input",  x_offset=-2.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="2", name="OUT", pin_type="Output", x_offset=2.0,  y_offset=0.0, orientation="E")],
                 ["NOT", "inverter", "logic", "ISA52"]),

                (dict(symbol_id="ISA52:TMR", standard_id=isa52_id, category_id=cat_lock,
                      name="Timer", reference_prefix="TMR", description="ISA 5.2 time delay element"),
                 [dict(pin_number="1", name="IN",  pin_type="Input",  x_offset=-2.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="2", name="OUT", pin_type="Output", x_offset=2.0,  y_offset=0.0, orientation="E"),
                  dict(pin_number="3", name="RST", pin_type="Input",  x_offset=0.0,  y_offset=-2.0, orientation="S")],
                 ["timer", "delay", "TMR", "time", "ISA52"]),
            ]
            for sym_data, pins, kws in _isa52:
                add_symbol(s, sym_data, pins, kws)


            # ── ISA 5.4 ──────────────────────────────────────────────────────
            isa54_id = stds["ISA 5.4"].id
            cat_loop = get_or_create_cat(s, isa54_id, "LOOP", "Loop symbols", 1)
            cat_conv = get_or_create_cat(s, isa54_id, "CONV", "Converters",   2)

            _isa54 = [
                (dict(symbol_id="ISA54:CONV_IP", standard_id=isa54_id, category_id=cat_conv,
                      name="Current to pneumatic converter", reference_prefix="IY",
                      isa_tag="IY", description="ISA 5.4 I/P converter — 4-20mA to 3-15 psi"),
                 [dict(pin_number="1", name="IN",  pin_type="Input",  x_offset=-2.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="2", name="OUT", pin_type="Output", x_offset=2.0,  y_offset=0.0, orientation="E"),
                  dict(pin_number="3", name="SUP", pin_type="Power",  x_offset=0.0,  y_offset=2.0, orientation="N")],
                 ["I/P", "converter", "current", "pneumatic", "4-20mA", "ISA54"]),
                (dict(symbol_id="ISA54:POSITIONER", standard_id=isa54_id, category_id=cat_loop,
                      name="Valve positioner", reference_prefix="ZY",
                      isa_tag="ZY", description="ISA 5.4 valve positioner — positions valve from control signal"),
                 [dict(pin_number="1", name="IN",  pin_type="Input",  x_offset=-2.0, y_offset=0.5,  orientation="W"),
                  dict(pin_number="2", name="FB",  pin_type="Input",  x_offset=-2.0, y_offset=-0.5, orientation="W"),
                  dict(pin_number="3", name="OUT", pin_type="Output", x_offset=2.0,  y_offset=0.0,  orientation="E")],
                 ["positioner", "valve", "ZY", "ISA54"]),
                (dict(symbol_id="ISA54:ANNUNCIATOR", standard_id=isa54_id, category_id=cat_loop,
                      name="Annunciator / alarm", reference_prefix="XA",
                      isa_tag="XA", description="ISA 5.4 annunciator panel alarm indicator"),
                 [dict(pin_number="1", name="IN",  pin_type="Input",  x_offset=-2.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="2", name="PWR", pin_type="Power",  x_offset=0.0,  y_offset=2.0, orientation="N")],
                 ["annunciator", "alarm", "XA", "indicator", "ISA54"]),
            ]
            for sym_data, pins, kws in _isa54:
                add_symbol(s, sym_data, pins, kws)

            # ── ISA 95 ───────────────────────────────────────────────────────
            isa95_id = stds["ISA 95"].id
            cat_l0 = get_or_create_cat(s, isa95_id, "L0", "Level 0 — Field devices", 1)
            cat_l1 = get_or_create_cat(s, isa95_id, "L1", "Level 1 — Basic control",  2)
            cat_l2 = get_or_create_cat(s, isa95_id, "L2", "Level 2 — Supervisory",    3)
            cat_l3 = get_or_create_cat(s, isa95_id, "L3", "Level 3 — MES",            4)

            _isa95 = [
                (dict(symbol_id="ISA95:PLC", standard_id=isa95_id, category_id=cat_l1,
                      name="Programmable Logic Controller", reference_prefix="PLC",
                      description="ISA 95 Level 1 basic control — PLC", width=8.0, height=6.0),
                 [dict(pin_number="1",  name="DI1",  pin_type="Input",  x_offset=-4.0, y_offset=2.0,  orientation="W"),
                  dict(pin_number="2",  name="DI2",  pin_type="Input",  x_offset=-4.0, y_offset=1.0,  orientation="W"),
                  dict(pin_number="3",  name="AI1",  pin_type="Input",  x_offset=-4.0, y_offset=0.0,  orientation="W"),
                  dict(pin_number="4",  name="DO1",  pin_type="Output", x_offset=4.0,  y_offset=2.0,  orientation="E"),
                  dict(pin_number="5",  name="DO2",  pin_type="Output", x_offset=4.0,  y_offset=1.0,  orientation="E"),
                  dict(pin_number="6",  name="AO1",  pin_type="Output", x_offset=4.0,  y_offset=0.0,  orientation="E"),
                  dict(pin_number="7",  name="NET",  pin_type="Bidirect",x_offset=0.0, y_offset=-3.0, orientation="S"),
                  dict(pin_number="8",  name="PWR",  pin_type="Power",  x_offset=0.0,  y_offset=3.0,  orientation="N")],
                 ["PLC", "controller", "programmable", "logic", "ISA95", "Level1"]),

                (dict(symbol_id="ISA95:HMI", standard_id=isa95_id, category_id=cat_l2,
                      name="Human Machine Interface", reference_prefix="HMI",
                      description="ISA 95 Level 2 supervisory — HMI / SCADA workstation", width=6.0, height=5.0),
                 [dict(pin_number="1", name="NET", pin_type="Bidirect", x_offset=0.0,  y_offset=-2.5, orientation="S"),
                  dict(pin_number="2", name="PWR", pin_type="Power",    x_offset=0.0,  y_offset=2.5,  orientation="N")],
                 ["HMI", "SCADA", "supervisory", "operator", "station", "ISA95", "Level2"]),

                (dict(symbol_id="ISA95:DCS", standard_id=isa95_id, category_id=cat_l1,
                      name="Distributed Control System", reference_prefix="DCS",
                      description="ISA 95 Level 1/2 — DCS controller node", width=8.0, height=6.0),
                 [dict(pin_number="1", name="I/O",  pin_type="Bidirect", x_offset=-4.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="2", name="NET",  pin_type="Bidirect", x_offset=4.0,  y_offset=0.0, orientation="E"),
                  dict(pin_number="3", name="PWR",  pin_type="Power",    x_offset=0.0,  y_offset=3.0, orientation="N")],
                 ["DCS", "distributed", "control", "ISA95"]),
            ]
            for sym_data, pins, kws in _isa95:
                add_symbol(s, sym_data, pins, kws)

            # ── IEC 60617 ────────────────────────────────────────────────────
            iec_id   = stds["IEC 60617"].id
            cat_sw   = get_or_create_cat(s, iec_id, "SWGR",  "Switchgear",    1)
            cat_mach = get_or_create_cat(s, iec_id, "MACH",  "Machines",      2)
            cat_prot = get_or_create_cat(s, iec_id, "PROT",  "Protection",    3)
            cat_xfmr = get_or_create_cat(s, iec_id, "XFMR",  "Transformers",  4)
            cat_term = get_or_create_cat(s, iec_id, "TERM",  "Terminals",     5)

            _iec = [
                (dict(symbol_id="IEC:CONTACTOR_3P", standard_id=iec_id, category_id=cat_sw,
                      name="Contactor 3-pole", reference_prefix="K", iec_code="IEC60617-S00200",
                      ansi_code="NEMA-M", description="3-pole power contactor with coil", width=6.0, height=8.0),
                 [dict(pin_number="A1", name="A1",  pin_type="Power",   x_offset=0.0,  y_offset=4.0,  orientation="N"),
                  dict(pin_number="A2", name="A2",  pin_type="Power",   x_offset=0.0,  y_offset=-4.0, orientation="S"),
                  dict(pin_number="1",  name="L1",  pin_type="Passive", x_offset=-3.0, y_offset=3.0,  orientation="W"),
                  dict(pin_number="2",  name="T1",  pin_type="Passive", x_offset=-3.0, y_offset=-3.0, orientation="W"),
                  dict(pin_number="3",  name="L2",  pin_type="Passive", x_offset=0.0,  y_offset=3.0,  orientation="N"),
                  dict(pin_number="4",  name="T2",  pin_type="Passive", x_offset=0.0,  y_offset=-3.0, orientation="S"),
                  dict(pin_number="5",  name="L3",  pin_type="Passive", x_offset=3.0,  y_offset=3.0,  orientation="E"),
                  dict(pin_number="6",  name="T3",  pin_type="Passive", x_offset=3.0,  y_offset=-3.0, orientation="E")],
                 ["contactor", "power", "3-pole", "IEC", "K", "motor starter"],
                 [dict(alias="Motor contactor", alias_type="name"), dict(alias="LC1", alias_type="trade")]),

                (dict(symbol_id="IEC:MOTOR_3P", standard_id=iec_id, category_id=cat_mach,
                      name="3-phase induction motor", reference_prefix="M", iec_code="IEC60617-M00001",
                      description="3-phase squirrel-cage induction motor", width=6.0, height=6.0),
                 [dict(pin_number="U", name="U",   pin_type="Power", x_offset=-3.0, y_offset=1.0,  orientation="W"),
                  dict(pin_number="V", name="V",   pin_type="Power", x_offset=-3.0, y_offset=0.0,  orientation="W"),
                  dict(pin_number="W", name="W",   pin_type="Power", x_offset=-3.0, y_offset=-1.0, orientation="W"),
                  dict(pin_number="PE", name="PE", pin_type="Ground",x_offset=0.0,  y_offset=-3.0, orientation="S")],
                 ["motor", "induction", "3-phase", "squirrel-cage", "IEC", "M"]),

                (dict(symbol_id="IEC:MCCB", standard_id=iec_id, category_id=cat_prot,
                      name="Moulded case circuit breaker", reference_prefix="QF", iec_code="IEC60617-S00101",
                      description="MCCB — overcurrent protection with thermal-magnetic trip", width=4.0, height=6.0),
                 [dict(pin_number="1", name="L1", pin_type="Power", x_offset=0.0, y_offset=3.0,  orientation="N"),
                  dict(pin_number="2", name="T1", pin_type="Power", x_offset=0.0, y_offset=-3.0, orientation="S")],
                 ["circuit breaker", "MCCB", "protection", "overcurrent", "QF", "IEC"]),

                (dict(symbol_id="IEC:OVERLOAD", standard_id=iec_id, category_id=cat_prot,
                      name="Thermal overload relay", reference_prefix="F", iec_code="IEC60617-S00301",
                      description="Thermal overload relay for motor protection", width=4.0, height=5.0),
                 [dict(pin_number="1",  name="L1",  pin_type="Passive", x_offset=0.0,  y_offset=2.5,  orientation="N"),
                  dict(pin_number="2",  name="T1",  pin_type="Passive", x_offset=0.0,  y_offset=-2.5, orientation="S"),
                  dict(pin_number="95", name="NC",  pin_type="Output",  x_offset=-2.0, y_offset=0.0,  orientation="W"),
                  dict(pin_number="96", name="NC",  pin_type="Output",  x_offset=-2.0, y_offset=-0.5, orientation="W"),
                  dict(pin_number="97", name="NO",  pin_type="Output",  x_offset=2.0,  y_offset=0.0,  orientation="E"),
                  dict(pin_number="98", name="NO",  pin_type="Output",  x_offset=2.0,  y_offset=-0.5, orientation="E")],
                 ["overload", "thermal", "relay", "motor protection", "F", "IEC"]),

                (dict(symbol_id="IEC:XFMR", standard_id=iec_id, category_id=cat_xfmr,
                      name="Power transformer", reference_prefix="T", iec_code="IEC60617-T00001",
                      description="Single-phase power transformer", width=5.0, height=6.0),
                 [dict(pin_number="1", name="HV+", pin_type="Power", x_offset=-2.5, y_offset=1.0,  orientation="W"),
                  dict(pin_number="2", name="HV-", pin_type="Power", x_offset=-2.5, y_offset=-1.0, orientation="W"),
                  dict(pin_number="3", name="LV+", pin_type="Power", x_offset=2.5,  y_offset=1.0,  orientation="E"),
                  dict(pin_number="4", name="LV-", pin_type="Power", x_offset=2.5,  y_offset=-1.0, orientation="E")],
                 ["transformer", "power", "step-down", "isolation", "T", "IEC"]),

                (dict(symbol_id="IEC:TERMINAL", standard_id=iec_id, category_id=cat_term,
                      name="Terminal block", reference_prefix="X", iec_code="IEC60617-S00401",
                      description="Single terminal block connection point", width=2.0, height=2.0),
                 [dict(pin_number="1", name="L", pin_type="Passive", x_offset=-1.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="2", name="R", pin_type="Passive", x_offset=1.0,  y_offset=0.0, orientation="E")],
                 ["terminal", "block", "connection", "X", "IEC"]),
            ]
            for sym_data, pins, kws, *rest in _iec:
                add_symbol(s, sym_data, pins, kws, rest[0] if rest else None)

            # ── ANSI/NEMA ────────────────────────────────────────────────────
            ansi_id   = stds["ANSI/NEMA"].id
            cat_pb    = get_or_create_cat(s, ansi_id, "PB",   "Push buttons",  1)
            cat_relay = get_or_create_cat(s, ansi_id, "RLY",  "Relays",        2)
            cat_fuse  = get_or_create_cat(s, ansi_id, "FUSE", "Fuses",         3)

            _ansi = [
                (dict(symbol_id="ANSI:PB_NO", standard_id=ansi_id, category_id=cat_pb,
                      name="Push button normally open", reference_prefix="PB", ansi_code="NEMA-PB-NO",
                      description="Momentary push button — normally open (start)"),
                 [dict(pin_number="1", name="1", pin_type="Passive", x_offset=-2.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="2", name="2", pin_type="Passive", x_offset=2.0,  y_offset=0.0, orientation="E")],
                 ["push button", "normally open", "NO", "start", "PB", "ANSI", "NEMA"]),

                (dict(symbol_id="ANSI:PB_NC", standard_id=ansi_id, category_id=cat_pb,
                      name="Push button normally closed", reference_prefix="PB", ansi_code="NEMA-PB-NC",
                      description="Momentary push button — normally closed (stop)"),
                 [dict(pin_number="1", name="1", pin_type="Passive", x_offset=-2.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="2", name="2", pin_type="Passive", x_offset=2.0,  y_offset=0.0, orientation="E")],
                 ["push button", "normally closed", "NC", "stop", "PB", "ANSI", "NEMA"]),

                (dict(symbol_id="ANSI:RELAY_COIL", standard_id=ansi_id, category_id=cat_relay,
                      name="Relay coil", reference_prefix="CR", ansi_code="NEMA-CR",
                      description="Control relay coil — NEMA style"),
                 [dict(pin_number="A1", name="A1", pin_type="Power", x_offset=-2.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="A2", name="A2", pin_type="Power", x_offset=2.0,  y_offset=0.0, orientation="E")],
                 ["relay", "coil", "CR", "control", "ANSI", "NEMA"]),

                (dict(symbol_id="ANSI:RELAY_NO", standard_id=ansi_id, category_id=cat_relay,
                      name="Relay contact normally open", reference_prefix="CR", ansi_code="NEMA-CR-NO",
                      description="Control relay NO contact — NEMA style"),
                 [dict(pin_number="1", name="1", pin_type="Passive", x_offset=-2.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="2", name="2", pin_type="Passive", x_offset=2.0,  y_offset=0.0, orientation="E")],
                 ["relay", "contact", "normally open", "NO", "ANSI", "NEMA"]),

                (dict(symbol_id="ANSI:FUSE", standard_id=ansi_id, category_id=cat_fuse,
                      name="Fuse", reference_prefix="FU", ansi_code="NEMA-FU",
                      description="Cartridge fuse — overcurrent protection"),
                 [dict(pin_number="1", name="1", pin_type="Passive", x_offset=-2.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="2", name="2", pin_type="Passive", x_offset=2.0,  y_offset=0.0, orientation="E")],
                 ["fuse", "overcurrent", "FU", "protection", "ANSI", "NEMA"]),
            ]
            for sym_data, pins, kws in _ansi:
                add_symbol(s, sym_data, pins, kws)

            # ── IEEE 315 ─────────────────────────────────────────────────────
            ieee_id   = stds["IEEE 315"].id
            cat_pass  = get_or_create_cat(s, ieee_id, "PASS",  "Passive components", 1)
            cat_semi  = get_or_create_cat(s, ieee_id, "SEMI",  "Semiconductors",     2)
            cat_logic = get_or_create_cat(s, ieee_id, "LOGIC", "Logic gates",        3)

            _ieee = [
                (dict(symbol_id="IEEE:R", standard_id=ieee_id, category_id=cat_pass,
                      name="Resistor", reference_prefix="R", ieee_code="IEEE315-R",
                      description="Fixed resistor", width=4.0, height=2.0),
                 [dict(pin_number="1", name="1", pin_type="Passive", x_offset=-2.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="2", name="2", pin_type="Passive", x_offset=2.0,  y_offset=0.0, orientation="E")],
                 ["resistor", "R", "passive", "IEEE315"]),

                (dict(symbol_id="IEEE:C", standard_id=ieee_id, category_id=cat_pass,
                      name="Capacitor", reference_prefix="C", ieee_code="IEEE315-C",
                      description="Fixed capacitor", width=2.0, height=4.0),
                 [dict(pin_number="1", name="+", pin_type="Passive", x_offset=0.0, y_offset=2.0,  orientation="N"),
                  dict(pin_number="2", name="-", pin_type="Passive", x_offset=0.0, y_offset=-2.0, orientation="S")],
                 ["capacitor", "C", "passive", "IEEE315"]),

                (dict(symbol_id="IEEE:L", standard_id=ieee_id, category_id=cat_pass,
                      name="Inductor", reference_prefix="L", ieee_code="IEEE315-L",
                      description="Fixed inductor / coil", width=4.0, height=2.0),
                 [dict(pin_number="1", name="1", pin_type="Passive", x_offset=-2.0, y_offset=0.0, orientation="W"),
                  dict(pin_number="2", name="2", pin_type="Passive", x_offset=2.0,  y_offset=0.0, orientation="E")],
                 ["inductor", "coil", "L", "passive", "IEEE315"]),

                (dict(symbol_id="IEEE:D", standard_id=ieee_id, category_id=cat_semi,
                      name="Diode", reference_prefix="D", ieee_code="IEEE315-D",
                      description="General purpose diode", width=3.0, height=3.0),
                 [dict(pin_number="A", name="A", pin_type="Input",  x_offset=-1.5, y_offset=0.0, orientation="W"),
                  dict(pin_number="K", name="K", pin_type="Output", x_offset=1.5,  y_offset=0.0, orientation="E")],
                 ["diode", "D", "semiconductor", "rectifier", "IEEE315"]),

                (dict(symbol_id="IEEE:NPN", standard_id=ieee_id, category_id=cat_semi,
                      name="NPN transistor", reference_prefix="Q", ieee_code="IEEE315-Q-NPN",
                      description="NPN bipolar junction transistor", width=4.0, height=5.0),
                 [dict(pin_number="B", name="B", pin_type="Input",  x_offset=-2.0, y_offset=0.0,  orientation="W"),
                  dict(pin_number="C", name="C", pin_type="Output", x_offset=0.0,  y_offset=2.5,  orientation="N"),
                  dict(pin_number="E", name="E", pin_type="Output", x_offset=0.0,  y_offset=-2.5, orientation="S")],
                 ["NPN", "transistor", "BJT", "Q", "semiconductor", "IEEE315"]),

                (dict(symbol_id="IEEE:AND", standard_id=ieee_id, category_id=cat_logic,
                      name="AND gate", reference_prefix="U", ieee_code="IEEE315-AND",
                      description="2-input AND logic gate", width=4.0, height=4.0),
                 [dict(pin_number="1", name="A",   pin_type="Input",  x_offset=-2.0, y_offset=1.0,  orientation="W"),
                  dict(pin_number="2", name="B",   pin_type="Input",  x_offset=-2.0, y_offset=-1.0, orientation="W"),
                  dict(pin_number="3", name="Y",   pin_type="Output", x_offset=2.0,  y_offset=0.0,  orientation="E"),
                  dict(pin_number="8", name="VCC", pin_type="Power",  x_offset=0.0,  y_offset=2.0,  orientation="N"),
                  dict(pin_number="7", name="GND", pin_type="Ground", x_offset=0.0,  y_offset=-2.0, orientation="S")],
                 ["AND", "gate", "logic", "U", "digital", "IEEE315"]),

                (dict(symbol_id="IEEE:OPAMP", standard_id=ieee_id, category_id=cat_semi,
                      name="Operational amplifier", reference_prefix="U", ieee_code="IEEE315-OA",
                      description="Generic op-amp symbol", width=5.0, height=5.0),
                 [dict(pin_number="2", name="IN-",  pin_type="Input",  x_offset=-2.5, y_offset=1.0,  orientation="W"),
                  dict(pin_number="3", name="IN+",  pin_type="Input",  x_offset=-2.5, y_offset=-1.0, orientation="W"),
                  dict(pin_number="6", name="OUT",  pin_type="Output", x_offset=2.5,  y_offset=0.0,  orientation="E"),
                  dict(pin_number="7", name="V+",   pin_type="Power",  x_offset=0.0,  y_offset=2.5,  orientation="N"),
                  dict(pin_number="4", name="V-",   pin_type="Power",  x_offset=0.0,  y_offset=-2.5, orientation="S")],
                 ["op-amp", "opamp", "amplifier", "U", "analog", "IEEE315"]),
            ]
            for sym_data, pins, kws in _ieee:
                add_symbol(s, sym_data, pins, kws)

            s.commit()

        stats = self.stats()
        total = sum(v for v in stats.values())
        logger.info("Library seeded: %d symbols across %d standards", total, len(stats))

    # ── Queries ───────────────────────────────────────────────────────────────

    def search(self, query: str, standard_code: Optional[str] = None, limit: int = 20) -> list[Symbol]:
        """
        Full-text symbol search by name, ISA tag, keyword, or alias.
        Optionally filter by standard code.
        """
        q = query.lower().strip()
        with self.session() as s:
            stmt = (
                select(Symbol)
                .distinct()
                .outerjoin(SymbolKeyword, Symbol.id == SymbolKeyword.symbol_id)
                .outerjoin(SymbolAlias,   Symbol.id == SymbolAlias.symbol_id)
                .where(Symbol.is_active == True)  # noqa: E712
                .where(or_(
                    Symbol.name.ilike(f"%{q}%"),
                    Symbol.symbol_id.ilike(f"%{q}%"),
                    Symbol.isa_tag.ilike(f"%{q}%"),
                    Symbol.description.ilike(f"%{q}%"),
                    SymbolKeyword.keyword.ilike(f"%{q}%"),
                    SymbolAlias.alias.ilike(f"%{q}%"),
                ))
            )
            if standard_code:
                stmt = stmt.join(Standard, Symbol.standard_id == Standard.id).where(
                    Standard.code == standard_code
                )
            stmt = stmt.limit(limit)
            return list(s.execute(stmt).scalars().all())

    def get_symbol(self, symbol_id: str) -> Optional[Symbol]:
        """Fetch a symbol by its unique symbol_id (e.g. 'ISA51:TIC')."""
        from sqlalchemy.orm import selectinload
        with self.session() as s:
            return s.execute(
                select(Symbol)
                .options(selectinload(Symbol.pins), selectinload(Symbol.keywords), selectinload(Symbol.aliases))
                .where(Symbol.symbol_id == symbol_id)
            ).scalar_one_or_none()

    def get_symbols_by_standard(self, standard_code: str) -> list[Symbol]:
        """Return all active symbols for a given standard."""
        with self.session() as s:
            return list(s.execute(
                select(Symbol)
                .join(Standard, Symbol.standard_id == Standard.id)
                .where(Standard.code == standard_code, Symbol.is_active == True)  # noqa: E712
                .order_by(Symbol.name)
            ).scalars().all())

    def get_categories(self, standard_code: str) -> list[Category]:
        """Return all categories for a standard, ordered by sort_order."""
        with self.session() as s:
            return list(s.execute(
                select(Category)
                .join(Standard, Category.standard_id == Standard.id)
                .where(Standard.code == standard_code)
                .order_by(Category.sort_order, Category.name)
            ).scalars().all())

    def get_line_types(self, standard_code: Optional[str] = None) -> list[LineType]:
        """Return all line types, optionally filtered by standard."""
        with self.session() as s:
            stmt = select(LineType).where(LineType.is_active == True)  # noqa: E712
            if standard_code:
                stmt = stmt.join(Standard, LineType.standard_id == Standard.id).where(
                    Standard.code == standard_code
                )
            return list(s.execute(stmt).scalars().all())

    def stats(self) -> dict[str, int]:
        """Return count of active symbols per standard."""
        with self.session() as s:
            rows = s.execute(
                select(Standard.code, func.count(Symbol.id))
                .outerjoin(Symbol, (Symbol.standard_id == Standard.id) & (Symbol.is_active == True))  # noqa: E712
                .group_by(Standard.code)
            ).all()
        return {code: count for code, count in rows}
