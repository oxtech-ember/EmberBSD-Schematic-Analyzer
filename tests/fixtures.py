"""Small hand-authored schematic and XML fixtures; no KiCad exporter is mocked here."""
import json
from pathlib import Path

ROOT = '00000000-0000-0000-0000-000000000001'
LEFT = '00000000-0000-0000-0000-000000000002'
RIGHT = '00000000-0000-0000-0000-000000000003'
A = '00000000-0000-0000-0000-000000000004'
B = '00000000-0000-0000-0000-000000000005'


def project(directory: Path):
    root = directory / 'root.kicad_sch'
    root.write_text(f'''(kicad_sch (version 20250114) (generator "eeschema")
      (uuid "{ROOT}") (paper "A4") (lib_symbols)
      (sheet (at 10 10) (size 20 20) (uuid "{LEFT}")
        (property "Sheetname" "Left") (property "Sheetfile" "child.kicad_sch"))
      (sheet (at 50 10) (size 20 20) (uuid "{RIGHT}")
        (property "Sheetname" "Right") (property "Sheetfile" "child.kicad_sch")))''')
    child = directory / 'child.kicad_sch'
    child.write_text(f'''(kicad_sch (version 20250114) (generator "eeschema")
      (uuid "00000000-0000-0000-0000-000000000099") (paper "A4")
      (lib_symbols (symbol "Test:TwoUnits"
        (symbol "TwoUnits_1_1"
          (pin input line (at 2 3 0) (length 1) (name "IN") (number "1")))
        (symbol "TwoUnits_2_1"
          (pin output line (at -4 1 180) (length 1) (name "OUT") (number "2")))))
      (symbol (lib_id "Test:TwoUnits") (at 10 20 90) (mirror x) (unit 1)
        (uuid "{A}") (property "Reference" "U1") (property "Value" "two")
        (pin "1" (uuid "00000000-0000-0000-0000-000000000010"))
        (instances (project "root"
          (path "/{ROOT}/{LEFT}" (reference "U1") (unit 1))
          (path "/{ROOT}/{RIGHT}" (reference "U2") (unit 1)))))
      (symbol (lib_id "Test:TwoUnits") (at 30 20 180) (unit 2)
        (uuid "{B}") (property "Reference" "U1") (property "Value" "two")
        (instances (project "root"
          (path "/{ROOT}/{LEFT}" (reference "U1") (unit 2))
          (path "/{ROOT}/{RIGHT}" (reference "U2") (unit 2)))))
      (junction (at 7 22) (diameter 0.4) (color 0 0 0 0) (uuid "junction"))
      (wire (pts (xy 7 22) (xy 34 22)) (stroke (width 0) (type default)) (uuid "wire"))
      (label "VCC" (at 7 22 0) (effects (font (size 1 1))) (uuid "label"))
      (no_connect (at 34 21) (uuid "nc"))
      (rule_area (uuid "unsupported")))''')
    netlist = directory / 'netlist.xml'
    netlist.write_text(f'''<?xml version="1.0"?><export version="E">
      <design><source>{root}</source><tool>Eeschema 10.0.8</tool></design>
      <components>
        <comp ref="U1"><value>two</value><sheetpath names="/Left/" tstamps="/{LEFT}/"/>
          <tstamps>{A} {B}</tstamps><units><unit name="A"><pins><pin num="1"/></pins></unit>
          <unit name="B"><pins><pin num="2"/></pins></unit></units></comp>
        <comp ref="U2"><value>two</value><sheetpath names="/Right/" tstamps="/{RIGHT}/"/>
          <tstamps>{A} {B}</tstamps></comp>
      </components><nets>
        <net code="1" name="VCC"><node ref="U1" pin="1" pinfunction="IN" pintype="input"/>
          <node ref="U2" pin="1" pinfunction="IN" pintype="input"/></net>
        <net code="2" name="unconnected-(U1-OUT-Pad2)"><node ref="U1" pin="2"
          pinfunction="OUT" pintype="output+no_connect"/></net>
      </nets></export>''')
    erc = directory / 'erc.json'
    erc.write_text(json.dumps({'source': root.name, 'kicad_version': '10.0.8', 'sheets': [
        {'path': '/', 'uuid_path': f'/{ROOT}', 'violations': []},
        {'path': '/Left/', 'uuid_path': f'/{ROOT}/{LEFT}', 'violations': []},
        {'path': '/Right/', 'uuid_path': f'/{ROOT}/{RIGHT}', 'violations': []}]}))
    return root, netlist, erc
