"""
miguel_angel — Component Library Database Models
Database Specialist implementation · Phase 2

SQLAlchemy 2.0 ORM models for the component symbol library.

Database: SQLite (embedded, no server, cross-platform)
Supports:  ISA 5.1 · ISA 5.2 · ISA 5.4 · ISA 95
           IEC 60617 · ANSI/NEMA · IEEE 315 · Custom

Schema overview:
  standards        — master list of supported standards
  categories       — component categories per standard
  symbols          — component symbol definitions
  pins             — pin definitions per symbol
  symbol_keywords  — full-text search keyword index
  symbol_aliases   — alternative names / cross-standard refs
  line_types       — ISA 5.1 / IEC signal and power line types
  manufacturers    — supplier / manufacturer master data
  manufacturer_parts — manufacturer part number → symbol mapping
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Index,
    Integer, String, Text, UniqueConstraint,
    event, text,
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, MappedColumn,
    relationship, mapped_column,
)


# ─────────────────────────────────────────────────────────────────────────────
# Base
# ─────────────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# Standard
# ─────────────────────────────────────────────────────────────────────────────

class Standard(Base):
    """
    Master list of supported standards.
    Seed data is inserted on first run by LibraryDB.seed_standards().
    """
    __tablename__ = "standards"

    id:           Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    code:         Mapped[str]           = mapped_column(String(32),  nullable=False, unique=True)
    name:         Mapped[str]           = mapped_column(String(128), nullable=False)
    organisation: Mapped[str]           = mapped_column(String(64),  nullable=False)
    scope:        Mapped[str]           = mapped_column(Text,        nullable=False, default="")
    region:       Mapped[str]           = mapped_column(String(32),  nullable=False, default="International")
    is_active:    Mapped[bool]          = mapped_column(Boolean,     nullable=False, default=True)

    categories: Mapped[list[Category]] = relationship("Category", back_populates="standard", cascade="all, delete-orphan")
    symbols:    Mapped[list[Symbol]]   = relationship("Symbol",   back_populates="standard")

    def __repr__(self) -> str:
        return f"<Standard {self.code}>"


# ─────────────────────────────────────────────────────────────────────────────
# Category
# ─────────────────────────────────────────────────────────────────────────────

class Category(Base):
    """
    Component category within a standard.
    e.g. standard=ISA 5.1 → category=Temperature indicator
    """
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("standard_id", "code", name="uq_category_std_code"),
    )

    id:          Mapped[int]          = mapped_column(Integer, primary_key=True, autoincrement=True)
    standard_id: Mapped[int]          = mapped_column(ForeignKey("standards.id"), nullable=False)
    code:        Mapped[str]          = mapped_column(String(32),  nullable=False)
    name:        Mapped[str]          = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    sort_order:  Mapped[int]          = mapped_column(Integer, nullable=False, default=0)

    standard: Mapped[Standard]     = relationship("Standard", back_populates="categories")
    symbols:  Mapped[list[Symbol]] = relationship("Symbol",   back_populates="category")

    def __repr__(self) -> str:
        return f"<Category {self.code} ({self.standard_id})>"


# ─────────────────────────────────────────────────────────────────────────────
# Symbol
# ─────────────────────────────────────────────────────────────────────────────

class Symbol(Base):
    """
    A reusable component symbol definition.
    One Symbol → many placed Component instances on schematic sheets.

    reference_prefix:  "K" for contactors, "TIC" for temp. controllers, "M" for motors
    isa_tag:           ISA 5.1 function tag (e.g. "TIC", "FCV", "PSV")
    iec_code:          IEC 60617 reference number
    ansi_code:         ANSI/NEMA designation
    ieee_code:         IEEE 315 reference
    svg_inline:        Inline SVG string for the symbol graphic
    width/height:      Canvas dimensions in logical units (1 unit = 2.5 mm)
    """
    __tablename__ = "symbols"
    __table_args__ = (
        UniqueConstraint("standard_id", "symbol_id", name="uq_symbol_std_sid"),
        Index("ix_symbol_name", "name"),
        Index("ix_symbol_category", "category_id"),
        Index("ix_symbol_standard", "standard_id"),
    )

    id:                Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol_id:         Mapped[str]           = mapped_column(String(64),  nullable=False)  # e.g. "ISA51:TIC"
    standard_id:       Mapped[int]           = mapped_column(ForeignKey("standards.id"), nullable=False)
    category_id:       Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"))
    name:              Mapped[str]           = mapped_column(String(128), nullable=False)
    reference_prefix:  Mapped[str]           = mapped_column(String(16),  nullable=False, default="X")
    description:       Mapped[Optional[str]] = mapped_column(Text)
    isa_tag:           Mapped[Optional[str]] = mapped_column(String(16))   # e.g. TIC, FCV, LI
    iec_code:          Mapped[Optional[str]] = mapped_column(String(32))   # IEC 60617 ref
    ansi_code:         Mapped[Optional[str]] = mapped_column(String(32))   # ANSI/NEMA ref
    ieee_code:         Mapped[Optional[str]] = mapped_column(String(32))   # IEEE 315 ref
    measured_variable: Mapped[Optional[str]] = mapped_column(String(4))    # ISA first-letter: T,P,F,L…
    function_letters:  Mapped[Optional[str]] = mapped_column(String(8))    # ISA subsequent: IC, CV, SH…
    svg_inline:        Mapped[Optional[str]] = mapped_column(Text)         # SVG symbol graphic
    svg_path:          Mapped[Optional[str]] = mapped_column(String(256))  # path to SVG file
    width:             Mapped[float]         = mapped_column(Float, nullable=False, default=4.0)
    height:            Mapped[float]         = mapped_column(Float, nullable=False, default=4.0)
    datasheet_url:     Mapped[Optional[str]] = mapped_column(String(512))
    is_active:         Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)
    is_verified:       Mapped[bool]          = mapped_column(Boolean, nullable=False, default=False)
    created_at:        Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=_now)
    updated_at:        Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    standard:  Mapped[Standard]             = relationship("Standard",  back_populates="symbols")
    category:  Mapped[Optional[Category]]   = relationship("Category",  back_populates="symbols")
    pins:      Mapped[list[SymbolPin]]      = relationship("SymbolPin", back_populates="symbol",
                                                           cascade="all, delete-orphan", order_by="SymbolPin.pin_number")
    keywords:  Mapped[list[SymbolKeyword]]  = relationship("SymbolKeyword", back_populates="symbol",
                                                           cascade="all, delete-orphan")
    aliases:   Mapped[list[SymbolAlias]]    = relationship("SymbolAlias",   back_populates="symbol",
                                                           cascade="all, delete-orphan")
    parts:     Mapped[list[ManufacturerPart]] = relationship("ManufacturerPart", back_populates="symbol")

    def __repr__(self) -> str:
        return f"<Symbol {self.symbol_id}: {self.name}>"


# ─────────────────────────────────────────────────────────────────────────────
# SymbolPin
# ─────────────────────────────────────────────────────────────────────────────

class SymbolPin(Base):
    """
    Pin definition for a symbol.
    Positions are in logical units relative to symbol origin (centre).
    orientation: N/S/E/W — direction the wire exits the pin.
    """
    __tablename__ = "symbol_pins"
    __table_args__ = (
        UniqueConstraint("symbol_id", "pin_number", name="uq_pin_symbol_number"),
    )

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol_id:   Mapped[int]           = mapped_column(ForeignKey("symbols.id"), nullable=False)
    pin_number:  Mapped[str]           = mapped_column(String(8),   nullable=False)
    name:        Mapped[str]           = mapped_column(String(32),  nullable=False)
    pin_type:    Mapped[str]           = mapped_column(String(16),  nullable=False, default="Passive")
    x_offset:    Mapped[float]         = mapped_column(Float,       nullable=False, default=0.0)
    y_offset:    Mapped[float]         = mapped_column(Float,       nullable=False, default=0.0)
    orientation: Mapped[str]           = mapped_column(String(1),   nullable=False, default="E")  # N/S/E/W
    description: Mapped[Optional[str]] = mapped_column(String(128))

    symbol: Mapped[Symbol] = relationship("Symbol", back_populates="pins")

    def __repr__(self) -> str:
        return f"<SymbolPin {self.pin_number} ({self.name}) on symbol {self.symbol_id}>"


# ─────────────────────────────────────────────────────────────────────────────
# SymbolKeyword
# ─────────────────────────────────────────────────────────────────────────────

class SymbolKeyword(Base):
    """
    Search keywords for full-text symbol lookup.
    e.g. symbol "TIC" → keywords: ["temperature", "indicator", "controller", "PID"]
    """
    __tablename__ = "symbol_keywords"
    __table_args__ = (
        UniqueConstraint("symbol_id", "keyword", name="uq_keyword_symbol"),
        Index("ix_keyword_word", "keyword"),
    )

    id:        Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id"), nullable=False)
    keyword:   Mapped[str] = mapped_column(String(64), nullable=False)

    symbol: Mapped[Symbol] = relationship("Symbol", back_populates="keywords")


# ─────────────────────────────────────────────────────────────────────────────
# SymbolAlias
# ─────────────────────────────────────────────────────────────────────────────

class SymbolAlias(Base):
    """
    Alternative names or cross-standard references for a symbol.
    e.g. ISA 5.1 "TIC" → IEC alias "Temperature Controller" → ANSI alias "TC"
    """
    __tablename__ = "symbol_aliases"

    id:         Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol_id:  Mapped[int]           = mapped_column(ForeignKey("symbols.id"), nullable=False)
    alias:      Mapped[str]           = mapped_column(String(64), nullable=False)
    alias_type: Mapped[str]           = mapped_column(String(32), nullable=False, default="name")
    # alias_type: "name" | "iec" | "ansi" | "ieee" | "legacy" | "trade"
    notes:      Mapped[Optional[str]] = mapped_column(String(256))

    symbol: Mapped[Symbol] = relationship("Symbol", back_populates="aliases")


# ─────────────────────────────────────────────────────────────────────────────
# LineType
# ─────────────────────────────────────────────────────────────────────────────

class LineType(Base):
    """
    Signal and power line type definitions.
    ISA 5.1 defines the signal line taxonomy.
    IEC 60617 defines power line conventions.
    """
    __tablename__ = "line_types"

    id:           Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    standard_id:  Mapped[int]           = mapped_column(ForeignKey("standards.id"), nullable=False)
    code:         Mapped[str]           = mapped_column(String(32), nullable=False, unique=True)
    name:         Mapped[str]           = mapped_column(String(128), nullable=False)
    description:  Mapped[Optional[str]] = mapped_column(Text)
    dash_pattern: Mapped[Optional[str]] = mapped_column(String(64))  # e.g. "8,4" = 8px on, 4px off
    line_weight:  Mapped[float]         = mapped_column(Float, nullable=False, default=1.0)
    color_hex:    Mapped[Optional[str]] = mapped_column(String(7))   # default render colour
    is_active:    Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<LineType {self.code}: {self.name}>"


# ─────────────────────────────────────────────────────────────────────────────
# Manufacturer
# ─────────────────────────────────────────────────────────────────────────────

class Manufacturer(Base):
    """Supplier / manufacturer master record."""
    __tablename__ = "manufacturers"

    id:      Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:    Mapped[str]           = mapped_column(String(128), nullable=False, unique=True)
    website: Mapped[Optional[str]] = mapped_column(String(256))
    country: Mapped[Optional[str]] = mapped_column(String(64))

    parts: Mapped[list[ManufacturerPart]] = relationship("ManufacturerPart", back_populates="manufacturer")


# ─────────────────────────────────────────────────────────────────────────────
# ManufacturerPart
# ─────────────────────────────────────────────────────────────────────────────

class ManufacturerPart(Base):
    """
    Maps a manufacturer's part number to a library symbol.
    Enables BOM generation with real part numbers and datasheets.
    """
    __tablename__ = "manufacturer_parts"
    __table_args__ = (
        UniqueConstraint("manufacturer_id", "part_number", name="uq_part_mfr_pn"),
        Index("ix_part_symbol", "symbol_id"),
    )

    id:              Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol_id:       Mapped[int]           = mapped_column(ForeignKey("symbols.id"), nullable=False)
    manufacturer_id: Mapped[int]           = mapped_column(ForeignKey("manufacturers.id"), nullable=False)
    part_number:     Mapped[str]           = mapped_column(String(64), nullable=False)
    description:     Mapped[Optional[str]] = mapped_column(String(256))
    datasheet_url:   Mapped[Optional[str]] = mapped_column(String(512))
    unit_price_usd:  Mapped[Optional[float]] = mapped_column(Float)
    is_preferred:    Mapped[bool]          = mapped_column(Boolean, nullable=False, default=False)

    symbol:       Mapped[Symbol]       = relationship("Symbol",       back_populates="parts")
    manufacturer: Mapped[Manufacturer] = relationship("Manufacturer", back_populates="parts")
