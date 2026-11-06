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
