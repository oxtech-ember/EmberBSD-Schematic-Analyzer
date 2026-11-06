import tempfile
import unittest
import json
from pathlib import Path

from ember_schematic.model import read_model
from fixtures import project, ROOT, LEFT, RIGHT, A, B


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.inputs = project(Path(self.temp.name))

    def test_repeated_instances_and_units_keep_identity(self):
        model = read_model(*self.inputs)
        self.assertIn('sheets', model)
        self.assertEqual(len(model['sheets']), 3)
        symbols = [s for sh in model['sheets'] for s in sh['symbols']]
        self.assertEqual({(s['sheet'], s['uuid'], s['reference'], s['unit']) for s in symbols},
                         {(f'/{LEFT}/', A, 'U1', 1), (f'/{LEFT}/', B, 'U1', 2),
                          (f'/{RIGHT}/', A, 'U2', 1), (f'/{RIGHT}/', B, 'U2', 2)})
        self.assertEqual(len({s['id'] for s in symbols}), 4)
        self.assertEqual(symbols[0]['pins'][0]['net'], '1')
        self.assertEqual(symbols[1]['pins'][0]['net'], '2')
        self.assertIsNone(symbols[3]['pins'][0]['net'])

    def test_asymmetric_pin_rotation_mirror_and_no_connect(self):
        model = read_model(*self.inputs)
        self.assertIn('sheets', model)
        sheet = model['sheets'][1]
        self.assertEqual(sheet['symbols'][0]['pins'][0]['at'], [7.0, 22.0])
        self.assertEqual(sheet['symbols'][1]['pins'][0]['at'], [34.0, 21.0])
        self.assertTrue(sheet['symbols'][1]['pins'][0]['no_connect'])
        self.assertEqual(sheet['junctions'][0]['diameter'], .4)
        self.assertEqual(sheet['wires'][0]['points'], [[7.0, 22.0], [34.0, 22.0]])
        self.assertEqual(sheet['labels'][0]['kind'], 'local')

    def test_unsupported_and_unmatched_are_explicit(self):
        model = read_model(*self.inputs)
        self.assertIn('coverage', model)
        reasons = {x['reason'] for x in model['coverage']}
        self.assertIn('unsupported:rule_area', reasons)
        self.assertIn('pin-not-exported', reasons)

    def test_mismatched_netlist_is_rejected(self):
        self.inputs[1].write_text(self.inputs[1].read_text().replace(A, 'foreign-uuid'))
        with self.assertRaisesRegex(ValueError, 'identity'):
            read_model(*self.inputs)

    def test_swapped_repeated_sheet_identities_are_rejected(self):
        netlist = self.inputs[1]
        text = netlist.read_text().replace(LEFT, 'SWAP').replace(RIGHT, LEFT).replace('SWAP', RIGHT)
        netlist.write_text(text)
        with self.assertRaisesRegex(ValueError, 'sheet.*identity'):
            read_model(*self.inputs)

    def test_units_of_one_component_may_span_sheets(self):
        child = self.inputs[0].parent / 'child.kicad_sch'
        data = child.read_text().replace(
            f'(path "/{ROOT}/{LEFT}" (reference "U1") (unit 2))',
            f'(path "/{ROOT}/{LEFT}" (reference "U2") (unit 2))').replace(
            f'(path "/{ROOT}/{RIGHT}" (reference "U2") (unit 2))',
            f'(path "/{ROOT}/{RIGHT}" (reference "U1") (unit 2))')
        child.write_text(data)
        model = read_model(*self.inputs)
        pin = model['sheets'][2]['symbols'][1]['pins'][0]
        self.assertEqual(pin['net'], '2')

    def test_erc_source_and_sheet_identity_are_checked(self):
        erc = self.inputs[2]
        for data in [dict(source='other.kicad_sch', sheets=[]),
                     dict(source='root.kicad_sch', sheets=[dict(uuid_path='/foreign/', violations=[])])]:
            erc.write_text(json.dumps(data))
            with self.subTest(data=data), self.assertRaisesRegex(ValueError, 'ERC.*identity'):
                read_model(*self.inputs)
        erc.write_text(json.dumps(dict(source='root.kicad_sch', sheets=[
            dict(path='/Left/', uuid_path=f'/{ROOT}/{LEFT}/', violations=[])])))
        self.assertEqual(read_model(*self.inputs)['erc']['source'], 'root.kicad_sch')

    def test_recursive_sheet_is_rejected(self):
        root = self.inputs[0]
        root.write_text(root.read_text().replace('child.kicad_sch', 'root.kicad_sch'))
        with self.assertRaisesRegex(ValueError, 'recursive'):
            read_model(*self.inputs)

    def test_design_files_stay_unchanged(self):
        directory = self.inputs[0].parent
        before = {p.name: p.read_bytes() for p in directory.glob('*.kicad_sch')}
        read_model(*self.inputs)
        self.assertEqual(before, {p.name: p.read_bytes() for p in directory.glob('*.kicad_sch')})

    def test_electrical_pin_type_comes_from_export(self):
        netlist = self.inputs[1]
        netlist.write_text(netlist.read_text().replace('pintype="input"', 'pintype="bidirectional"'))
        model = read_model(*self.inputs)
        pin = model['sheets'][1]['symbols'][0]['pins'][0]
        self.assertEqual(pin['electrical_type'], 'bidirectional')

    def test_power_symbol_remains_in_drawing_when_omitted_from_xml(self):
        root = self.inputs[0]
        data = root.read_text().rstrip()
        root.write_text(data[:-1] + '''(symbol (lib_id "power:GND") (at 10 10 0)
          (uuid "power") (property "Reference" "#PWR01")) )''')
        model = read_model(*self.inputs)
        self.assertEqual(model['sheets'][0]['symbols'][0]['reference'], '#PWR01')
        self.assertIsNone(model['sheets'][0]['symbols'][0]['electrical'])
        self.assertIn('symbol-not-exported', {c['reason'] for c in model['coverage']})
