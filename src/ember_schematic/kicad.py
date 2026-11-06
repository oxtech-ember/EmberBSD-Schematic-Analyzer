"""Fresh schematic exports through the public KiCad CLI."""
from pathlib import Path
import shutil
import subprocess
import tempfile


def export_electrical(root: Path, tool: str, output: Path):
    root = Path(root).resolve()
    if root.suffix != '.kicad_sch' or not root.is_file():
        raise ValueError('input must be an existing .kicad_sch file')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='kicad-', dir=output))
    netlist, erc = stage / 'netlist.xml', stage / 'erc.json'
    commands = [
        [tool, 'sch', 'export', 'netlist', '--format', 'kicadxml', '--output', str(netlist), str(root)],
        [tool, 'sch', 'erc', '--format', 'json', '--severity-all', '--output', str(erc), str(root)],
    ]
    try:
        for args, destination in zip(commands, (netlist, erc)):
            subprocess.run(args, check=True, capture_output=True, text=True)
            if not destination.is_file() or destination.stat().st_size == 0:
                raise ValueError(f'KiCad did not produce {destination.name}')
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        shutil.rmtree(stage)
        detail = getattr(error, 'stderr', None) or str(error)
        raise ValueError(f'KiCad export failed: {detail.strip()}') from error
    return netlist, erc
