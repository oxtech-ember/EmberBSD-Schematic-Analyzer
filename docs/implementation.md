# Schematic Analyzer Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` for implementation;
> routine source/log work and independent review may use the already requested
> Luna subagents. Preserve the shared SDK, prefixes, build objects and caches.

**Goal:** Read a KiCad schematic, expose its electrical and drawing models, and
produce explainable checks and visual evidence without changing the input.

**Architecture:** KiCad exports electrical netlist/ERC. A KiUtils adapter reads
geometry and identities. One application model joins these sources, then graph
analysis and explicit electrical rules produce JSON and sheet reports.

**Tech Stack:** Python standard library, common KiUtils 1.4.8 with the Ports
junction fix, KiCad 10.0.8 CLI; no web service, GUI toolkit or database.

**Spec:** [design.md](design.md).

## Global constraints

- Schematics only; no PCB analysis or automatic design edits.
- Keep geometry and electrical authority distinct; no second net resolver.
- Keep sheet instance, UUID, unit and pin identities; report unsupported data.
- Treat missing facts as unknown, not successful checks or inferred ratings.
- Publish common dependency fixes through Ports; do not vendor them here.
- Use the selected SDK Python for host work; package and test the runtime on EmberBSD.

## Review focus

- Repeated child sheets share source UUIDs but have distinct instance paths.
- Multi-unit and rotated/mirrored pins must join the correct physical source anchor.
- A plain crossing, branch and label connection must not become a wire cycle.
- Incomplete symbols or new drawing elements must reduce coverage explicitly.
- KiCad export failure or stale/mismatching identities must never yield a clean report.

## Task 1: Import a correlated model

Files: `src/ember_schematic/model.py`, `kicad.py`, `drawing.py`, and
`tests/test_model.py`, `tests/test_kicad.py`, `tests/fixtures/`.

Interfaces: `export_electrical(root: Path, tool: str, output: Path)` runs KiCad and
returns paths to fresh XML and ERC JSON; `read_model(root: Path, netlist: Path,
erc: Path) -> dict` produces the JSON-compatible model. KiUtils remains the
only schematic parser. Subprocess calls use argument lists and explicit outputs.

- [x] Add fixtures/assertions for repeated sheets, multi-unit pins, mirrored and
  rotated anchors, power/virtual symbols, no-connect and unsupported tokens.
- [x] Implement the adapters and identity joins, retaining source geometry and
  recording unresolved associations instead of fabricating nets.
- [x] Check export failures and inconsistent identities, then run the model tests.
- [x] Commit the model and its documented JSON fields together.

## Task 2: Analyze the wire drawing

Files: `src/ember_schematic/wires.py`, `orientation.py`, `tests/test_wires.py`,
`tests/test_orientation.py`.

Interfaces: `analyze_wires(model: dict) -> list[dict]` and
`suggest_orientations(model: dict) -> list[dict]`. Findings contain source IDs,
sheet, geometry, measured values, conditions and severity/category.

- [x] Assert a T branch is not a cycle; crossing and junction fixtures differ;
  virtual label joins add no geometric edges; duplicate wire and closed loop differ.
- [x] Build the contact/section graph and a deterministic cycle basis; retain
  anchors when measuring chains, lengths and bend counts.
- [x] Measure candidate symbol rotations using actual pin transforms; return
  unknown/no recommendation when drawing context cannot support the comparison.
- [x] Run graph/orientation regressions and commit.

## Task 3: Add explicit electrical rules

Files: `src/ember_schematic/rules.py`, `tests/test_rules.py`,
`examples/constraints.json`.

Interface: `check_electrical(model: dict, facts: dict) -> list[dict]`.
Facts explicitly identify rail voltages, allowed pin ranges and required
pull-up/decoupling connections. Findings cite the facts used.

- [x] Test a declared overvoltage, compatible input and missing rating.
- [x] Test a required resistor/capacitor connection, wrong/missing connection and
  insufficient component identity; do not infer roles from reference prefixes.
- [x] Implement these bounded rules, retain ERC results separately and commit.

## Task 4: Deliver CLI, reports and integration

Files: `src/ember_schematic/__main__.py`, `report.py`, `pyproject.toml`,
`tests/test_cli.py`, `tests/test_report.py`, `README.md`.

Interface: `schematic-analyzer ROOT --output DIR [--kicad-cli PATH]
[--constraints FILE]` writes `model.json`, `report.json` and a sheet-oriented
visual report. A failed input/export returns nonzero; findings and unknowns
remain visible in the report rather than being reported as processing errors.

- [ ] Exercise a real small KiCad design through export, analysis and report;
  verify source files are unchanged and highlighted objects match source IDs.
- [x] Document precise coverage and unsupported elements; distinguish actual
  measurements from candidate layout improvements.
- [ ] Package the application through Ports with the common KiUtils dependency.
- [ ] Run the workflow on EmberBSD aarch64, then publish reviewed sources and
  dependency-closed packages through the explicit maintainer publisher.

Current implementation: model, graph analysis, bounded rules, CLI and reports pass 29 host regressions. The complete KiCad export/runtime workflow and the Ports application package remain open in the project integration work; no target acceptance is implied.
