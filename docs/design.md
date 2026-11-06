# Schematic analysis

The goal is to give an AI agent a faithful, inspectable model of a KiCad schematic
and provide deterministic checks with evidence. The same report should let a
person locate the affected part of the drawing. PCB tracks, copper layers, vias
and footprint placement are outside this project.

## Inputs and ownership

The ordinary command reads a root `.kicad_sch` project. KiCad 10.0.8 CLI exports
fresh XML netlist and ERC JSON to a temporary output directory. KiUtils 1.4.8 with
the common Ports junction patch reads drawing geometry. There is one electrical
authority: KiCad. The application does not implement another net resolver.

Use a small Python application with KiUtils as its only Python runtime library.
KiCad is an external runtime tool. The application and its tests have their own
repository; dependency recipes and shared patches belong to Ports. No SDK
internals, private repository, online service or LLM is required to run it.

The application will use GPL-3.0, consistent with its KiUtils dependency.
This is an implementation choice, not a change to EmberBSD's OS license.

## Two views of one schematic

The electrical view contains components, units, pins, nets, pin electrical types,
fields and explicit constraints. Preserve KiCad's exported names and identities.
Pin types do not establish current direction or a block's purpose. Power/virtual
symbols omitted by the XML exporter remain drawing objects; missing electrical
associations must be visible rather than invented.

The drawing view contains wires, junctions, labels, bus entries, no-connect
markers and symbol/pin transforms. Identity includes the sheet instance path,
source object UUID, unit and pin number as applicable. Repeated sheet instances
must not collapse into one object. Label connectivity is virtual and must not
be counted as a drawn wire or wire cycle.

Geometry is a graph of contacts and wire sections, not a graph joining every
pair of objects in an electrical net. Split a wire at actual junctions, endpoint
contacts, and pin/label anchors. A crossing without a connection remains two
paths. A branch is not a loop. Duplicate overlapping segments are reported
separately from nonzero-area cycles.

## Checks and recommendations

The first drawing checks identify wire-cycle candidates, duplicate segments,
and measured detours/bends in chains between anchors. Show the actual source
segments and affected anchors. Connectivity preservation is necessary for a
simplification, but does not by itself prove a clearer drawing.

Symbol-rotation recommendations use real pin locations and compare candidate
orientations, wiring effort and drawing context. They are suggestions, not
automatic edits. Do not recommend an orientation when pin transforms, text
obstacles or sheet context are incomplete. Wire length on a schematic is a
readability metric, not a PCB length, delay or signal-integrity measurement.

Electrical checks supplement ERC. Start with explicit project facts: allowed
voltage ranges and required pull-ups/decoupling connections. Every finding names
its input facts and affected pins/nets. Without the required component/rail data,
report unknown rather than assume a voltage from a net name or rate a component
from its reference prefix. AI interpretations remain separate from measured facts.

## Outputs and limits

Produce a JSON model/report and a visual graph/report by schematic sheet, with
source UUIDs and coordinates. All outputs go to the requested output directory;
source designs are never rewritten. Unsupported document elements are recorded
in coverage. In particular, KiUtils does not fully model newer rule areas, tables,
groups or embedded fonts; do not silently present its view as a lossless drawing.

## Alternatives considered

KiCad CLI plus a common file-model library is the chosen small implementation.
A KiCad C++ exporter extension would offer deeper native data, but requires a
larger integration change; use it only for a demonstrated missing interface.
The standalone kicad-tools parser has a larger dependency set and its additional
router/PCB machinery does not solve this schematic-only task. A private copy or
new parser of the KiCad format would duplicate existing work.

## Acceptance

Use real KiCad 10 input plus small public fixtures: branch, connected/unconnected
crossing, label-only connection, repeated hierarchy and multi-unit symbol,
rotated/mirrored asymmetric pins, drawn wire loop, and no-connect marker.
Compare electrical joins with actual KiCad export/ERC; verify original files
are unchanged. Distinguish pure Python host tests from the complete workflow on
EmberBSD aarch64. The latter requires the Ports KiCad package to be ready.
