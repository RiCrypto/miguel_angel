"""
Tests for miguel_angel core — data model, netlist engine, ERC, file I/O.
Run with: pytest tests/test_core.py -v
"""

import json
import tempfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from miguel_angel.core import (
    Point, BoundingBox, Pin, Component, ComponentProperties,
    WireSegment, Net, NetLabel, Sheet, TitleBlock, Project,
    ProjectMetadata, LibrarySymbol, Standard, ComponentCategory,
    LineType, PinType, Orientation, SheetSize,
    NetlistEngine, ERCViolation, MAprojIO, FileIOError,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def make_pin(name: str, x: float, y: float, pin_type: PinType = PinType.PASSIVE) -> Pin:
    return Pin(name=name, position=Point(x=x, y=y), pin_type=pin_type)


def make_component(ref: str, x: float, y: float, pins: list[Pin]) -> Component:
    return Component(
        symbol_id="lib:test",
        reference=ref,
        position=Point(x=x, y=y),
        pins=pins,
        category=ComponentCategory.RELAY,
        standard=Standard.IEC_60617,
    )


def make_wire(x1: float, y1: float, x2: float, y2: float) -> WireSegment:
    return WireSegment(start=Point(x=x1, y=y1), end=Point(x=x2, y=y2))


def simple_project() -> Project:
    """
    Minimal project:
      K1 (pin A at (0,0), pin B at (4,0))
      K2 (pin A at (4,0), pin B at (8,0))
      Wire connecting K1.B to K2.A at x=4
    """
    pin_k1_a = make_pin("A", 0, 0)
    pin_k1_b = make_pin("B", 4, 0)
    pin_k2_a = make_pin("A", 0, 0)
    pin_k2_b = make_pin("B", 4, 0)

    k1 = make_component("K1", 0, 0, [pin_k1_a, pin_k1_b])
    k2 = make_component("K2", 4, 0, [pin_k2_a, pin_k2_b])

    wire = make_wire(4, 0, 4, 0)   # zero-length wire = direct join at (4,0)

    sheet = Sheet(
        name="Sheet 1",
        components=[k1, k2],
        wires=[wire],
    )
    return Project(
        metadata=ProjectMetadata(name="Test Project", author="pytest"),
        sheets=[sheet],
    )


# ─── Point tests ──────────────────────────────────────────────────────────────

class TestPoint:
    def test_equality(self):
        assert Point(x=1.0, y=2.0) == Point(x=1.0, y=2.0)

    def test_addition(self):
        p = Point(x=1, y=2) + Point(x=3, y=4)
        assert p == Point(x=4, y=6)

    def test_distance(self):
        p1 = Point(x=0, y=0)
        p2 = Point(x=3, y=4)
        assert abs(p1.distance_to(p2) - 5.0) < 1e-9


class TestBoundingBox:
    def test_center(self):
        bb = BoundingBox(x=0, y=0, width=4, height=4)
        assert bb.center == Point(x=2, y=2)

    def test_contains(self):
        bb = BoundingBox(x=0, y=0, width=10, height=10)
        assert bb.contains(Point(x=5, y=5))
        assert not bb.contains(Point(x=11, y=5))


# ─── Component tests ──────────────────────────────────────────────────────────

class TestComponent:
    def test_rotation_snapped(self):
        c = make_component("K1", 0, 0, [])
        c.rotation = 45.0
        c2 = Component(**c.model_dump())
        assert c2.rotation in (0.0, 90.0)

    def test_get_pin_by_name(self):
        pin = make_pin("L1", 0, 0)
        comp = make_component("K1", 0, 0, [pin])
        assert comp.get_pin_by_name("L1") == pin
        assert comp.get_pin_by_name("XX") is None

    def test_absolute_pin_position_no_rotation(self):
        pin  = make_pin("A", 2, 0)
        comp = make_component("K1", 5, 5, [pin])
        abs_pos = comp.absolute_pin_position(pin)
        assert abs(abs_pos.x - 7.0) < 1e-6
        assert abs(abs_pos.y - 5.0) < 1e-6

    def test_absolute_pin_position_90_degrees(self):
        pin  = make_pin("A", 2, 0)
        comp = make_component("K1", 0, 0, [pin])
        comp.rotation = 90.0
        abs_pos = comp.absolute_pin_position(pin)
        # Rotated 90°: (2,0) → (0,2)
        assert abs(abs_pos.x - 0.0) < 1e-4
        assert abs(abs_pos.y - 2.0) < 1e-4


# ─── Wire tests ───────────────────────────────────────────────────────────────

class TestWireSegment:
    def test_horizontal_wire(self):
        w = make_wire(0, 0, 10, 0)
        assert w.is_horizontal is True

    def test_vertical_wire(self):
        w = make_wire(5, 0, 5, 8)
        assert w.is_horizontal is False

    def test_diagonal_wire_raises(self):
        with pytest.raises(ValueError, match="horizontal or vertical"):
            WireSegment(start=Point(x=0, y=0), end=Point(x=3, y=4))

    def test_length(self):
        w = make_wire(0, 0, 10, 0)
        assert abs(w.length - 10.0) < 1e-9

    def test_shares_endpoint(self):
        w1 = make_wire(0, 0, 5, 0)
        w2 = make_wire(5, 0, 10, 0)
        assert w1.shares_endpoint(w2)

    def test_no_shared_endpoint(self):
        w1 = make_wire(0, 0, 5, 0)
        w2 = make_wire(6, 0, 10, 0)
        assert not w1.shares_endpoint(w2)


# ─── Net tests ────────────────────────────────────────────────────────────────

class TestNet:
    def test_name_not_empty(self):
        with pytest.raises(ValueError):
            Net(name="   ")

    def test_name_stripped(self):
        n = Net(name="  L1  ")
        assert n.name == "L1"

    def test_net_with_pins(self):
        n = Net(name="24VDC", pin_ids=["p1", "p2", "p3"])
        assert len(n.pin_ids) == 3


# ─── Sheet tests ──────────────────────────────────────────────────────────────

class TestSheet:
    def test_component_count(self):
        comps = [make_component(f"K{i}", i, 0, []) for i in range(5)]
        sheet = Sheet(name="Test", components=comps)
        assert sheet.component_count == 5

    def test_get_component(self):
        pin  = make_pin("A", 0, 0)
        comp = make_component("K1", 0, 0, [pin])
        sheet = Sheet(name="Test", components=[comp])
        assert sheet.get_component(comp.id) is comp
        assert sheet.get_component("nonexistent") is None


# ─── Project tests ────────────────────────────────────────────────────────────

class TestProject:
    def test_total_components(self):
        proj = simple_project()
        assert proj.total_components == 2

    def test_total_wires(self):
        proj = simple_project()
        assert proj.total_wires == 1

    def test_get_component_anywhere(self):
        proj = simple_project()
        comp = proj.sheets[0].components[0]
        found = proj.get_component_anywhere(comp.id)
        assert found is comp

    def test_get_sheet(self):
        proj  = simple_project()
        sheet = proj.sheets[0]
        assert proj.get_sheet(sheet.id) is sheet
        assert proj.get_sheet("bad_id") is None


# ─── NetlistEngine tests ──────────────────────────────────────────────────────

class TestNetlistEngine:

    def test_build_creates_nodes(self):
        proj   = simple_project()
        engine = NetlistEngine()
        engine.build(proj)
        # 2 components × 2 pins each = 4 nodes
        assert engine.graph.number_of_nodes() == 4

    def test_connected_pins_joined(self):
        """K1.B and K2.A both sit at absolute (4,0) — should be connected."""
        proj   = simple_project()
        engine = NetlistEngine()
        engine.build(proj)

        k1 = proj.sheets[0].components[0]
        k2 = proj.sheets[0].components[1]
        pin_k1_b = k1.pins[1]   # B at relative (4,0) → absolute (4,0)
        pin_k2_a = k2.pins[0]   # A at relative (0,0) → absolute (4,0)

        assert engine.is_connected(pin_k1_b.id, pin_k2_a.id)

    def test_unconnected_pins_not_connected(self):
        proj   = simple_project()
        engine = NetlistEngine()
        engine.build(proj)

        k1 = proj.sheets[0].components[0]
        k2 = proj.sheets[0].components[1]
        pin_k1_a = k1.pins[0]   # at absolute (0,0)
        pin_k2_b = k2.pins[1]   # at absolute (8,0)

        assert not engine.is_connected(pin_k1_a.id, pin_k2_b.id)

    def test_net_names_assigned(self):
        proj   = simple_project()
        engine = NetlistEngine()
        engine.build(proj)
        assert len(proj.nets) > 0
        for net in proj.nets:
            assert net.name  # no empty names

    def test_unconnected_pins_detected(self):
        proj   = simple_project()
        engine = NetlistEngine()
        engine.build(proj)
        # K1.A and K2.B are unconnected (degree 0)
        unconn = engine.unconnected_pins()
        assert len(unconn) == 2

    def test_net_summary_returns_list(self):
        proj   = simple_project()
        engine = NetlistEngine()
        engine.build(proj)
        summary = engine.net_summary()
        assert isinstance(summary, list)
        assert all("net_name" in item for item in summary)

    def test_netlist_dict_export(self):
        proj   = simple_project()
        engine = NetlistEngine()
        engine.build(proj)
        export = engine.to_netlist_dict()
        assert "nets" in export
        assert "components" in export
        assert export["format"].startswith("miguel_angel netlist")

    def test_erc_warns_unconnected_pins(self):
        proj       = simple_project()
        engine     = NetlistEngine()
        engine.build(proj)
        violations = engine.run_erc()
        erc001 = [v for v in violations if v.code == "ERC-001"]
        assert len(erc001) >= 2   # K1.A and K2.B

    def test_erc_error_output_conflict(self):
        """Two output pins on the same net → ERC-004."""
        pin_a = make_pin("OUT", 2, 0, PinType.OUTPUT)
        pin_b = make_pin("OUT", 0, 0, PinType.OUTPUT)
        comp_a = make_component("U1", 0, 0, [pin_a])
        comp_b = make_component("U2", 2, 0, [pin_b])
        sheet  = Sheet(name="ERC Test", components=[comp_a, comp_b])
        proj   = Project(
            metadata=ProjectMetadata(name="ERC Test"),
            sheets=[sheet],
        )
        engine = NetlistEngine()
        engine.build(proj)
        violations = engine.run_erc()
        erc004 = [v for v in violations if v.code == "ERC-004"]
        assert len(erc004) >= 1

    def test_net_label_connects_wires(self):
        """Same net label name on two wires connects them electrically."""
        pin_a = make_pin("X", 0, 0)
        pin_b = make_pin("X", 0, 0)
        comp_a = make_component("C1", 0, 0, [pin_a])
        comp_b = make_component("C2", 10, 0, [pin_b])

        label_a = NetLabel(net_name="MAINS", position=Point(x=0, y=0))
        label_b = NetLabel(net_name="MAINS", position=Point(x=10, y=0))

        sheet = Sheet(
            name="Label Test",
            components=[comp_a, comp_b],
            net_labels=[label_a, label_b],
        )
        proj = Project(
            metadata=ProjectMetadata(name="Label Test"),
            sheets=[sheet],
        )
        engine = NetlistEngine()
        engine.build(proj)
        assert engine.is_connected(pin_a.id, pin_b.id)


# ─── MAprojIO tests ───────────────────────────────────────────────────────────

class TestMAprojIO:

    def test_save_and_load_roundtrip(self, tmp_path):
        proj = simple_project()
        path = tmp_path / "test.maproj"
        io   = MAprojIO()
        io.save(proj, path)
        loaded = io.load(path)
        assert loaded.metadata.name == proj.metadata.name
        assert len(loaded.sheets) == len(proj.sheets)
        assert loaded.sheets[0].component_count == proj.sheets[0].component_count

    def test_save_creates_file(self, tmp_path):
        proj = simple_project()
        path = tmp_path / "project.maproj"
        MAprojIO().save(proj, path)
        assert path.exists()

    def test_save_creates_backup(self, tmp_path):
        proj = simple_project()
        path = tmp_path / "project.maproj"
        io   = MAprojIO()
        io.save(proj, path)
        io.save(proj, path)      # second save → backup created
        bak  = path.with_suffix(".maproj.bak")
        assert bak.exists()

    def test_load_nonexistent_raises(self, tmp_path):
        with pytest.raises(FileIOError, match="not found"):
            MAprojIO().load(tmp_path / "missing.maproj")

    def test_load_invalid_version_raises(self, tmp_path):
        path = tmp_path / "bad.maproj"
        path.write_text(json.dumps({"version": "99", "metadata": {}, "sheets": [], "nets": []}))
        with pytest.raises(FileIOError, match="Unsupported"):
            MAprojIO().load(path)

    def test_load_malformed_json_raises(self, tmp_path):
        path = tmp_path / "bad.maproj"
        path.write_text("{ this is not json }")
        with pytest.raises(FileIOError):
            MAprojIO().load(path)

    def test_new_project_has_one_sheet(self):
        proj = MAprojIO.new_project("Test", author="Ricardo")
        assert len(proj.sheets) == 1
        assert proj.metadata.author == "Ricardo"

    def test_json_is_human_readable(self, tmp_path):
        proj = simple_project()
        path = tmp_path / "readable.maproj"
        MAprojIO().save(proj, path)
        text = path.read_text(encoding="utf-8")
        # Should be indented JSON
        assert "\n  " in text
        assert '"version"' in text

    def test_metadata_only_read(self, tmp_path):
        proj = simple_project()
        path = tmp_path / "project.maproj"
        MAprojIO().save(proj, path)
        meta = MAprojIO.read_metadata_only(path)
        assert meta is not None
        assert meta.name == "Test Project"

    def test_serialisation_preserves_nets(self, tmp_path):
        proj   = simple_project()
        engine = NetlistEngine()
        engine.build(proj)
        path   = tmp_path / "netlist.maproj"
        io     = MAprojIO()
        io.save(proj, path)
        loaded = io.load(path)
        assert len(loaded.nets) == len(proj.nets)

    def test_is_maproj(self):
        assert MAprojIO.is_maproj(Path("project.maproj"))
        assert MAprojIO.is_maproj(Path("project.maproj.bin"))
        assert not MAprojIO.is_maproj(Path("project.txt"))
