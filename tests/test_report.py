import json
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

from ember_schematic.model import read_model
from ember_schematic.report import write_report
from ember_schematic.wires import analyze_wires
from fixtures import project


class ReportTests(unittest.TestCase):
    def test_json_and_svg_preserve_graph_and_escape_source_text(self):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            model = read_model(*project(directory))
            model['sheets'][1]['labels'][0]['text'] = '<script>alert("x")</script>'
            findings = analyze_wires(model)
            report = dict(findings=findings, orientations=[], electrical_checks='not-requested')
            out = directory / 'report'
            write_report(model, report, out)
            self.assertTrue((out / 'model.json').is_file())
            self.assertIn('wire_graph', json.loads((out / 'model.json').read_text())['sheets'][1])
            image = out / 'sheet-002.svg'
            tree = ET.parse(image)
            text = ''.join(tree.getroot().itertext())
            self.assertIn('<script>alert("x")</script>', text)
            self.assertNotIn('<script>', image.read_text())
            self.assertNotIn('<script>', (out / 'index.html').read_text())
            self.assertIn('not-requested', (out / 'index.html').read_text())

    def test_failed_analysis_does_not_replace_a_previous_report(self):
        from ember_schematic.__main__ import main
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            root, _, _ = project(directory)
            out = directory / 'report'
            out.mkdir()
            (out / 'model.json').write_text('previous')
            result = main([str(root), '--output', str(out), '--kicad-cli', str(directory / 'missing')])
            self.assertNotEqual(result, 0)
            self.assertEqual((out / 'model.json').read_text(), 'previous')

    def test_output_symlink_cannot_overwrite_input(self):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            inputs = project(directory)
            before = inputs[0].read_bytes()
            out = directory / 'report'
            out.mkdir()
            (out / 'model.json').symlink_to(inputs[0])
            model = read_model(*inputs)
            write_report(model, dict(findings=[], orientations=[], electrical_checks='not-requested'), out)
            self.assertEqual(inputs[0].read_bytes(), before)
