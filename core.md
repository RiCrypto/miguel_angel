# `miguel_angel.core`

The schematic engine — Pydantic v2 data models, NetworkX netlist, and `.maproj` file I/O.

---

## Data models (`core.models`)

### Geometry

#### `Point`

```python
from miguel_angel.core import Point

p = Point(x=10.0, y=5.0)
p.distance_to(Point(x=13.0, y=9.0))  # → 5.0
p + Point(x=1, y=1)                  # → Point(x=11.0, y=6.0)
```

#### `BoundingBox`

```python
from miguel_angel.core import BoundingBox

bb = BoundingBox(x=0, y=0, width=10, height=10)
bb.center       # → Point(x=5.0, y=5.0)
bb.contains(Point(x=5, y=5))  # → True
```

### Enumerations

| Enum | Values |
|------|--------|
| `Standard` | `ISA_5_1`, `ISA_5_2`, `ISA_5_4`, `ISA_95`, `IEC_60617`, `ANSI_NEMA`, `IEEE_315`, `CUSTOM` |
| `ComponentCategory` | `INDICATOR`, `CONTROLLER`, `TRANSMITTER`, `VALVE`, `SWITCH`, `CONTACTOR`, `MOTOR`, `PLC`, `HMI`, `RESISTOR`, … |
| `LineType` | `PROCESS_CONNECTION`, `PNEUMATIC_SIGNAL`, `ELECTRIC_SIGNAL`, `HIGH_VOLTAGE`, `CONTROL_WIRE`, `GROUND_PE`, … |
| `PinType` | `INPUT`, `OUTPUT`, `POWER`, `GROUND`, `BIDIRECT`, `PASSIVE`, `SIGNAL` |
| `SheetSize` | `A4`, `A3`, `A2`, `A1`, `A0`, `ANSI_A`, `ANSI_B`, `ANSI_D`, `CUSTOM` |

### `Pin`

```python
from miguel_angel.core import Pin, PinType, Point

pin = Pin(
    name="L1",
    pin_type=PinType.POWER,
    position=Point(x=-3, y=0),
    orientation="W",    # N / S / E / W
)
```

**Fields:** `id`, `name`, `number`, `pin_type`, `position`, `orientation`, `net_id`

### `Component`

```python
from miguel_angel.core import Component, ComponentCategory, Standard, Point

comp = Component(
    symbol_id="IEC:CONTACTOR_3P",
    reference="K1",
    position=Point(x=10, y=5),
    rotation=0.0,           # snapped to 0/90/180/270
    mirrored=False,
    category=ComponentCategory.CONTACTOR,
    standard=Standard.IEC_60617,
)

# Compute absolute canvas position of a pin (accounts for rotation + mirror)
abs_pos = comp.absolute_pin_position(comp.pins[0])
```

**Fields:** `id`, `symbol_id`, `reference`, `category`, `standard`, `position`, `rotation`,
`mirrored`, `pins`, `properties`, `bounding_box`, `sheet_id`, `locked`

### `WireSegment`

```python
from miguel_angel.core import WireSegment, Point, LineType

wire = WireSegment(
    start=Point(x=14, y=5),
    end=Point(x=20, y=5),    # must be horizontal or vertical
    line_type=LineType.PROCESS_CONNECTION,
)
wire.is_horizontal  # → True
wire.length         # → 6.0
```

**Validation:** diagonal wires raise `ValueError`. Use two segments for a right-angle turn.

### `Net`

```python
from miguel_angel.core import Net

net = Net(name="L1", pin_ids=["uuid-1", "uuid-2"])
```

**Fields:** `id`, `name`, `pin_ids`, `wire_ids`, `net_class`, `color`, `voltage`, `notes`

### `NetLabel`

```python
from miguel_angel.core import NetLabel, Point

label = NetLabel(net_name="24VDC", position=Point(x=20, y=5))
```

Two labels with the same `net_name` anywhere in the project are electrically connected.

### `Sheet`

```python
from miguel_angel.core import Sheet, TitleBlock, SheetSize

sheet = Sheet(
    name="Sheet 1 — Power circuit",
    size=SheetSize.A4,
    title_block=TitleBlock(
        title="Motor Starter",
        drawn_by="R. Almeida",
        revision="A",
        date="2025-06-24",
    ),
    components=[k1, m1],
    wires=[wire1, wire2],
    net_labels=[label1],
)
```

### `Project`

```python
from miguel_angel.core import Project, ProjectMetadata

project = Project(
    metadata=ProjectMetadata(
        name="Motor Starter",
        author="R. Almeida",
        organisation="Acme Engineering",
        standard=Standard.IEC_60617,
    ),
    sheets=[sheet1],
    nets=[],
)

project.total_components  # → sum across all sheets
project.get_sheet(sheet_id)
project.get_component_anywhere(component_id)
```

---

## Netlist engine (`core.netlist`)

### `NetlistEngine`

```python
from miguel_angel.core import NetlistEngine

engine = NetlistEngine()
engine.build(project)          # full rebuild from project model
engine.update_sheet(sheet, project)  # partial rebuild for one sheet

# Connectivity queries
engine.is_connected(pin_a.id, pin_b.id)      # → bool
engine.get_net_for_pin(pin_id)               # → "L1" or None
engine.get_connected_pins(pin_id)            # → [pin_id, ...]
engine.unconnected_pins()                    # → [{pin_id, component_ref, ...}]
engine.net_summary()                         # → [{net_name, pin_count, pins}]

# ERC
violations = engine.run_erc()               # → [ERCViolation, ...]

# Export
netlist_dict = engine.to_netlist_dict()     # → KiCad-compatible dict
```

### `ERCViolation`

| Attribute | Type | Description |
|-----------|------|-------------|
| `code` | `str` | `"ERC-001"` through `"ERC-004"` |
| `message` | `str` | Human-readable description |
| `severity` | `str` | `"error"`, `"warning"`, `"info"` |
| `component_id` | `str \| None` | UUID of the affected component |
| `pin_id` | `str \| None` | UUID of the affected pin |
| `net_id` | `str \| None` | Net name |
| `sheet_id` | `str \| None` | Sheet UUID |

**ERC rules:**

| Code | Name | Severity |
|------|------|---------|
| ERC-001 | Unconnected pin | Warning |
| ERC-002 | Dead-end wire (single-pin net) | Warning |
| ERC-003 | Power-to-power short | Error |
| ERC-004 | Output conflict (multiple outputs on same net) | Error |

---

## File I/O (`core.fileio`)

### `MAprojIO`

```python
from miguel_angel.core import MAprojIO
from pathlib import Path

io = MAprojIO()

# Create a blank project
project = MAprojIO.new_project("Motor Starter", author="R. Almeida")

# Save (writes JSON + optional msgpack sidecar + .bak backup)
io.save(project, Path("motor_starter.maproj"))

# Load
project = io.load(Path("motor_starter.maproj"))

# Fast metadata preview (no full parse)
meta = MAprojIO.read_metadata_only(Path("motor_starter.maproj"))
# → ProjectMetadata(name="Motor Starter", ...)

# Check if a file is a .maproj
MAprojIO.is_maproj(Path("file.maproj"))      # → True
MAprojIO.is_maproj(Path("file.maproj.bin"))  # → True
```

**File format:**

- `.maproj` — UTF-8 JSON, 2-space indented, human-readable, git-diffable
- `.maproj.bin` — msgpack binary sidecar (written when project > 1 MB, read preferentially)
- `.maproj.bak` — previous version backup (one generation kept)
