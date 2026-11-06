# Model contract

`read_model(root, netlist, erc)` accepts KiCad XML format E and ERC JSON.
The ordinary CLI generates both exports afresh; imported test fixtures are not
evidence of a successful KiCad runtime invocation.

The JSON has `components`, `nets`, `sheets`, original `erc`, and `coverage`.
Electrical net IDs and pin membership come exclusively from KiCad. A missing
membership is `null`; an explicitly unconnected exported net is retained.

Sheet IDs are KiCad XML instance paths (`/` for the root, child sheet UUIDs for
descendants). Source-file UUIDs do not identify sheet instances. Symbol IDs join
that path with the symbol UUID; pin IDs additionally carry unit and pin number.
The `sheet`, `uuid`, `unit`, `number`, and pin `uuid` fields remain separate.
Component references are resolved from the full schematic instance paths,
which include the root UUID in the schematic file (unlike XML sheet paths).

Coordinates and lengths are millimetres, X right and Y down on the sheet.
Pins retain their library-local coordinates, angle, length and electrical type.
Symbol transforms convert library Y-up coordinates into the sheet frame before
rotation and sheet-axis reflection. Embedded definitions are used; unresolved
inheritance is marked in coverage. Body styles select their actual unit pins.

Drawing data preserves wires, buses, labels with their scopes, junctions,
no-connects, sheet pins, symbol bodies and decorations. It is an analysis model,
not a lossless serializer or a replacement renderer for KiCad. `coverage` names
unsupported source elements and missing associations. Power/virtual symbols can
be absent from XML and remain present in the drawing.

The source hashes identify files read for the drawing; they are not a proof that
externally supplied XML is current. UUID mismatches are rejected. No original
schematic, project or library is written by the application.

`analyze_wires(model)` adds `wire_graph` to each sheet: numbered nodes with
coordinates and anchor IDs, and edges with endpoints, length and original wire
IDs. It reports a deterministic cycle basis, overlapping wire sections and
chain detours. Labels add anchors but never edges between distant points; hidden
pins do not create drawing contacts. Lower bounds ignore obstacles and are not
proposed replacement routes.

Orientation output compares quarter-turn pin-distance lower bounds only when
each relevant pin has one traceable wire chain to a fixed anchor. It deliberately
returns `unknown` for a rotation recommendation: checking symbol body and text
clearance is not implemented. Measurements remain usable without claiming that
the shorter orientation is safe or clearer. This limit is also in every result.

Explicit constraints use the format in `examples/constraints.json`. Net names
must identify one exported net. Pin ratings and rail voltages are supplied by the
project; conflicting or absent facts produce `unknown`. Required pull-up and
decoupling checks verify only the declared component's two-pin net connection,
not its value, type, physical placement, population, frequency response or
adequacy for an IC. A `pass` applies only to that narrow rule, not to the design.
