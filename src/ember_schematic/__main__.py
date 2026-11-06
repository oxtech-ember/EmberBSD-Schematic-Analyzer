import argparse
import json
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET

from .kicad import export_electrical
from .model import read_model
from .orientation import suggest_orientations
from .report import write_report
from .rules import check_electrical
from .wires import analyze_wires


def main(argv=None):
    parser = argparse.ArgumentParser(description='Read-only KiCad schematic analysis')
    parser.add_argument('root', type=Path, help='root .kicad_sch')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--kicad-cli', default='kicad-cli')
    parser.add_argument('--constraints', type=Path, help='explicit voltage and connection facts, JSON')
    args = parser.parse_args(argv)
    try:
        facts = json.loads(args.constraints.read_text(encoding='utf-8')) if args.constraints else {}
        with tempfile.TemporaryDirectory(prefix='schematic-analysis-') as stage:
            netlist, erc = export_electrical(args.root, args.kicad_cli, Path(stage))
            model = read_model(args.root, netlist, erc)
        findings = analyze_wires(model) + check_electrical(model, facts)
        report = dict(schema=1, source=model['source'], findings=findings,
                      orientations=suggest_orientations(model),
                      electrical_checks='explicit-facts-only' if args.constraints else 'not-requested')
        write_report(model, report, args.output)
    except (OSError, ValueError, ET.ParseError) as error:
        print(f'schematic-analyzer: {error}', file=sys.stderr)
        return 1
    print(f'{len(model["sheets"])} sheet instances, {len(model["components"])} components, '
          f'{len(findings)} rule results; report: {args.output / "index.html"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
