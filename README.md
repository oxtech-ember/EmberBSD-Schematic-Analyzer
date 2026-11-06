# EmberBSD Schematic Analyzer

A read-only analyzer for KiCad **schematics**, intended for people and AI agents.
It combines the electrical netlist produced by KiCad with the source drawing's
wires, junctions, labels, symbol transforms and hierarchical instance identities.
It does not analyze PCB routing.

The first implementation imports repeated sheet instances and multi-unit symbols,
correlates their pins with KiCad XML, exposes physical wire graphs, measures loops,
overlapping wires and detours, and checks explicitly declared electrical facts.
It produces JSON, HTML and per-sheet SVG graphs. This is experimental: the full
KiCad workflow on EmberBSD aarch64 still awaits the KiCad Ports build.

## Run

Use Python 3.11+ with the shared KiUtils package and KiCad 10 CLI available.
EmberBSD Ports `cad/py-kiutils` 1.4.8nb1 includes the common junction-diameter
fix; the parser is not vendored in this application. From this checkout:

```sh
PYTHONPATH=src python3 -m ember_schematic project.kicad_sch --output report
```

`--kicad-cli /path/to/kicad-cli` selects the executable.
`--constraints examples/constraints.json` enables bounded electrical checks;
replace the example's identities and ratings with verified facts for your design.
No cloud, LLM, database or GUI session is needed. The installed entry point is
`schematic-analyzer`; it has the same arguments.

Open `report/index.html`. `model.json` exposes components, nets, drawing objects
and wire graphs; `report.json` contains check results and orientation measurements.
Original files are never rewritten. Failed imports/exports return nonzero.
Exit zero means analysis ran, not that a design passed electrical review.

## Limits

- Wire cycles and detours are readability candidates, not proven electrical errors.
  Label-based connections are never turned into physical wires or loops.
- Rotation output compares pin-distance lower bounds. Symbol/text clearance and
  rerouting are unverified, so it does not recommend a rotation or edit the schematic.
- Voltage limits, supply values and required connections must be supplied explicitly.
  A connection check does not verify a capacitor/resistor value or circuit function.
- Unsupported elements and missing associations are visible in `coverage`.
  Newer rule areas, tables, groups and embedded fonts are not fully modeled.
- SVG is a wire graph with pin anchors, not a complete rendering of symbol bodies.

See the [model contract](docs/model.md) and [design](docs/design.md).
Only schematic files are accepted; PCB routing is outside the application.

## Development

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Host tests cover repeated hierarchy, unit identity, mirrored/rotated pins,
crossings, loops, overlaps, unknown facts, export failures and escaped reports.
Geometry import has also read 90 demonstration schematic files shipped with
KiCad 10.0.8, including a 73-sheet-instance project. These checks do not establish
successful native KiCad export or target runtime acceptance.

License: GPL-3.0-only. KiUtils is a separately packaged GPL-3.0 dependency.
