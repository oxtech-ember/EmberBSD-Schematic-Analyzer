import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import subprocess

from ember_schematic.kicad import export_electrical


class ExportTests(unittest.TestCase):
    def test_failed_export_cannot_reuse_old_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            root = directory / 'a.kicad_sch'
            root.write_text('(kicad_sch)')
            (directory / 'netlist.xml').write_text('old export')
            with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, [], stderr='bad input')):
                with self.assertRaisesRegex(ValueError, 'KiCad.*bad input'):
                    export_electrical(root, 'kicad-cli', directory)

    def test_export_is_schematic_only_with_fresh_output_names(self):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            root = directory / 'name with spaces.kicad_sch'
            root.write_text('(kicad_sch)')
            seen = []

            def run(args, **kwargs):
                seen.append(args)
                self.assertEqual(args[0:2], ['kicad-cli', 'sch'])
                self.assertEqual(args[-1], str(root.resolve()))
                out = Path(args[args.index('--output') + 1])
                self.assertFalse(out.exists())
                out.write_text('<export version="E"/>' if 'netlist' in args else '{"sheets":[]}')
                return subprocess.CompletedProcess(args, 0, '', '')

            with patch('subprocess.run', side_effect=run):
                first = export_electrical(root, 'kicad-cli', directory)
                second = export_electrical(root, 'kicad-cli', directory)
            self.assertNotEqual(first, second)
            self.assertTrue(all(p.is_file() for p in first + second))
            self.assertIn('kicadxml', seen[0])
            self.assertIn('json', seen[1])
            self.assertIn('--severity-all', seen[1])
