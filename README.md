# EmberBSD Schematic Analyzer

A read-only analyzer for KiCad **schematics**, intended for people and AI agents.
It combines the electrical netlist produced by KiCad with the source drawing's
wires, junctions, labels, symbol transforms and hierarchical instance identities.
It does not analyze PCB routing.

Implementation is in progress. The current scope is in [the design](docs/design.md)
and the [implementation plan](docs/implementation.md); no finished CLI is claimed.
KiCad supplies electrical connectivity and ERC. KiUtils is a shared dependency,
not vendored here. The EmberBSD Ports provider includes the junction-diameter fix.

The analyzer will report measurements, source references, candidate simplifications
and unknowns. A graphical wire loop is not automatically an electrical error,
and the program will not rewrite the input design.
