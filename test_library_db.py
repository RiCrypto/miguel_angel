"""
Tests for miguel_angel component library database.
Run with: pytest tests/test_library_db.py -v
"""

import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from miguel_angel.db import LibraryDB, Symbol, Standard, Category, LineType


@pytest.fixture
def db(tmp_path):
    """Fresh in-memory-equivalent library DB for each test."""
    library = LibraryDB(db_path=tmp_path / "test_library.db")
    library.connect(seed=True)
    yield library
    library.close()


# ─── Schema tests ─────────────────────────────────────────────────────────────

class TestSchema:
    def test_tables_created(self, db):
        from sqlalchemy import inspect
        insp = inspect(db._engine)
        tables = insp.get_table_names()
        expected = ["standards", "categories", "symbols", "symbol_pins",
                    "symbol_keywords", "symbol_aliases", "line_types",
                    "manufacturers", "manufacturer_parts"]
        for t in expected:
            assert t in tables, f"Missing table: {t}"

    def test_foreign_keys_enabled(self, db):
        from sqlalchemy import text
        with db.session() as s:
            result = s.execute(text("PRAGMA foreign_keys")).scalar()
        assert result == 1


# ─── Standards seed tests ─────────────────────────────────────────────────────

class TestStandards:
    def test_all_seven_standards_seeded(self, db):
        stats = db.stats()
        expected = ["ISA 5.1", "ISA 5.2", "ISA 5.4", "ISA 95",
                    "IEC 60617", "ANSI/NEMA", "IEEE 315", "Custom"]
        for std in expected:
            assert std in stats, f"Standard '{std}' not seeded"

    def test_isa51_has_symbols(self, db):
        stats = db.stats()
        assert stats["ISA 5.1"] >= 10

    def test_iec_has_symbols(self, db):
        stats = db.stats()
        assert stats["IEC 60617"] >= 5

    def test_ansi_has_symbols(self, db):
        stats = db.stats()
        assert stats["ANSI/NEMA"] >= 4

    def test_ieee_has_symbols(self, db):
        stats = db.stats()
        assert stats["IEEE 315"] >= 6

    def test_isa52_has_symbols(self, db):
        stats = db.stats()
        assert stats["ISA 5.2"] >= 3

    def test_isa95_has_symbols(self, db):
        stats = db.stats()
        assert stats["ISA 95"] >= 2

    def test_seed_is_idempotent(self, db):
        """Seeding twice must not duplicate data."""
        db.seed_standards()
        db.seed_symbols()
        stats_before = db.stats()
        db.seed_standards()
        db.seed_symbols()
        stats_after = db.stats()
        assert stats_before == stats_after


# ─── Symbol tests ─────────────────────────────────────────────────────────────

class TestSymbols:
    def test_get_tic_symbol(self, db):
        sym = db.get_symbol("ISA51:TIC")
        assert sym is not None
        assert sym.name == "Temperature indicator controller"
        assert sym.isa_tag == "TIC"
        assert sym.measured_variable == "T"
        assert sym.function_letters == "IC"

    def test_tic_has_pins(self, db):
        sym = db.get_symbol("ISA51:TIC")
        assert sym is not None
        assert len(sym.pins) == 4

    def test_tic_has_keywords(self, db):
        sym = db.get_symbol("ISA51:TIC")
        assert sym is not None
        kws = [k.keyword for k in sym.keywords]
        assert "temperature" in kws
        assert "controller" in kws

    def test_tic_has_aliases(self, db):
        sym = db.get_symbol("ISA51:TIC")
        assert sym is not None
        aliases = [a.alias for a in sym.aliases]
        assert "TC" in aliases

    def test_get_nonexistent_symbol_returns_none(self, db):
        assert db.get_symbol("FAKE:SYMBOL") is None

    def test_contactor_symbol_exists(self, db):
        sym = db.get_symbol("IEC:CONTACTOR_3P")
        assert sym is not None
        assert sym.reference_prefix == "K"
        assert len(sym.pins) == 8

    def test_plc_symbol_exists(self, db):
        sym = db.get_symbol("ISA95:PLC")
        assert sym is not None
        assert len(sym.pins) == 8

    def test_transistor_symbol_exists(self, db):
        sym = db.get_symbol("IEEE:NPN")
        assert sym is not None
        assert sym.reference_prefix == "Q"
        assert len(sym.pins) == 3

    def test_resistor_symbol_exists(self, db):
        sym = db.get_symbol("IEEE:R")
        assert sym is not None
        assert sym.reference_prefix == "R"

    def test_fuse_symbol_exists(self, db):
        sym = db.get_symbol("ANSI:FUSE")
        assert sym is not None
        assert sym.reference_prefix == "FU"


# ─── Pin tests ────────────────────────────────────────────────────────────────

class TestPins:
    def test_pins_ordered_by_number(self, db):
        sym = db.get_symbol("ISA51:TIC")
        assert sym is not None
        nums = [p.pin_number for p in sym.pins]
        assert nums == sorted(nums)

    def test_pin_orientations_valid(self, db):
        valid = {"N", "S", "E", "W"}
        sym = db.get_symbol("ISA51:TIC")
        assert sym is not None
        for pin in sym.pins:
            assert pin.orientation in valid

    def test_pin_types_valid(self, db):
        valid = {"Input", "Output", "Power", "Ground", "Passive", "Bidirectional", "Signal", "Bidirect"}
        sym = db.get_symbol("ISA95:PLC")
        assert sym is not None
        for pin in sym.pins:
            assert pin.pin_type in valid, f"Unknown pin type: {pin.pin_type}"


# ─── Search tests ──────────────────────────────────────────────────────────────

class TestSearch:
    def test_search_temperature(self, db):
        results = db.search("temperature")
        assert len(results) >= 3
        names = [r.name.lower() for r in results]
        assert any("temperature" in n for n in names)

    def test_search_by_isa_tag(self, db):
        results = db.search("TIC")
        assert any(r.symbol_id == "ISA51:TIC" for r in results)

    def test_search_by_keyword(self, db):
        results = db.search("PID")
        assert any(r.symbol_id == "ISA51:TIC" for r in results)

    def test_search_by_alias(self, db):
        results = db.search("motor contactor")
        assert any(r.symbol_id == "IEC:CONTACTOR_3P" for r in results)

    def test_search_filtered_by_standard(self, db):
        results = db.search("indicator", standard_code="ISA 5.1")
        for r in results:
            assert r.standard_id is not None
            with db.session() as s:
                from sqlalchemy import select
                std = s.execute(select(Standard).where(Standard.id == r.standard_id)).scalar_one()
            assert std.code == "ISA 5.1"

    def test_search_empty_returns_empty(self, db):
        results = db.search("xyznotacomponent999")
        assert results == []

    def test_search_respects_limit(self, db):
        results = db.search("i", limit=5)
        assert len(results) <= 5

    def test_search_case_insensitive(self, db):
        r1 = db.search("TEMPERATURE")
        r2 = db.search("temperature")
        assert len(r1) == len(r2)


# ─── Category tests ───────────────────────────────────────────────────────────

class TestCategories:
    def test_isa51_has_categories(self, db):
        cats = db.get_categories("ISA 5.1")
        assert len(cats) >= 4
        codes = [c.code for c in cats]
        assert "IND"  in codes
        assert "CTRL" in codes
        assert "VALV" in codes

    def test_iec_has_categories(self, db):
        cats = db.get_categories("IEC 60617")
        assert len(cats) >= 3

    def test_categories_sorted_by_order(self, db):
        cats = db.get_categories("ISA 5.1")
        orders = [c.sort_order for c in cats]
        assert orders == sorted(orders)

    def test_symbols_by_standard(self, db):
        syms = db.get_symbols_by_standard("ISA 5.1")
        assert len(syms) >= 10
        assert all(isinstance(s, Symbol) for s in syms)


# ─── Line type tests ──────────────────────────────────────────────────────────

class TestLineTypes:
    def test_isa51_signal_lines_seeded(self, db):
        lts = db.get_line_types("ISA 5.1")
        codes = [lt.code for lt in lts]
        assert "ISA51_PROCESS"  in codes
        assert "ISA51_PNEUMATIC" in codes
        assert "ISA51_ELECTRIC"  in codes
        assert "ISA51_HYDRAULIC" in codes

    def test_iec_power_lines_seeded(self, db):
        lts = db.get_line_types("IEC 60617")
        codes = [lt.code for lt in lts]
        assert "IEC_HV"      in codes
        assert "IEC_CONTROL" in codes
        assert "IEC_GROUND_PE" in codes

    def test_process_line_is_solid(self, db):
        lts = db.get_line_types("ISA 5.1")
        process = next((lt for lt in lts if lt.code == "ISA51_PROCESS"), None)
        assert process is not None
        assert process.dash_pattern is None
        assert process.line_weight >= 1.5

    def test_pneumatic_line_is_dashed(self, db):
        lts = db.get_line_types("ISA 5.1")
        pneum = next((lt for lt in lts if lt.code == "ISA51_PNEUMATIC"), None)
        assert pneum is not None
        assert pneum.dash_pattern is not None

    def test_all_line_types_have_names(self, db):
        lts = db.get_line_types()
        assert len(lts) >= 10
        for lt in lts:
            assert lt.name


# ─── Stats tests ──────────────────────────────────────────────────────────────

class TestStats:
    def test_stats_returns_dict(self, db):
        stats = db.stats()
        assert isinstance(stats, dict)

    def test_total_symbols_reasonable(self, db):
        stats = db.stats()
        total = sum(stats.values())
        assert total >= 30, f"Expected at least 30 symbols, got {total}"

    def test_no_standard_is_empty(self, db):
        stats = db.stats()
        for std, count in stats.items():
            if std != "Custom":
                assert count > 0, f"Standard '{std}' has no symbols"
