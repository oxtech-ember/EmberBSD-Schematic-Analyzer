"""Correlate electrical exports with schematic instances without resolving nets."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from .drawing import read_drawing


def read_model(root: Path, netlist: Path, erc: Path) -> dict:
    root = Path(root).resolve()
    xml = ET.parse(netlist).getroot()
    if xml.tag != 'export' or xml.get('version') != 'E' or xml.find('nets') is None:
        raise ValueError('expected KiCad XML netlist format E')
    source = xml.findtext('design/source')
    if not source or Path(source).name != root.name:
        raise ValueError('netlist source does not match schematic')
    erc_data = json.loads(Path(erc).read_text(encoding='utf-8'))
    if not isinstance(erc_data, dict) or not isinstance(erc_data.get('sheets'), list):
        raise ValueError('expected KiCad ERC JSON with sheets')
    sheets, coverage = read_drawing(root)
    components = {}
    for c in xml.findall('components/comp'):
        ref = c.get('ref')
        if not ref or ref in components:
            raise ValueError('missing or duplicate component reference')
        sp = c.find('sheetpath')
        components[ref] = dict(reference=ref, value=c.findtext('value'),
                               uuids=(c.findtext('tstamps') or '').split(),
                               sheet=sp.get('tstamps') if sp is not None else None,
                               fields={f.get('name'): f.text for f in c.findall('fields/field')},
                               units=[dict(name=u.get('name'), pins=[p.get('num') for p in u.findall('pins/pin')])
                                      for u in c.findall('units/unit')])
    nets, by_pin, pin_metadata = [], {}, {}
    codes = set()
    for n in xml.findall('nets/net'):
        code = n.get('code')
        if code is None or code in codes:
            raise ValueError('missing or duplicate net code')
        codes.add(code)
        nodes = []
        for node in n.findall('node'):
            ref, pin = node.get('ref'), node.get('pin')
            if ref not in components or not pin:
                raise ValueError('netlist node has no component/pin identity')
            key = (ref, pin)
            if key in by_pin and by_pin[key] != code:
                raise ValueError('pin belongs to multiple exported nets')
            by_pin[key] = code
            pin_metadata[key] = node.attrib
            nodes.append(dict(reference=ref, pin=pin, function=node.get('pinfunction'),
                              electrical_type=node.get('pintype')))
        nets.append(dict(id=code, name=n.get('name'), nodes=nodes))
    seen = set()
    for sheet in sheets:
        for symbol in sheet['symbols']:
            ref = symbol['reference']
            component = components.get(ref)
            if component is None:
                coverage.append(dict(sheet=sheet['id'], object=symbol['id'],
                                     reason='symbol-not-exported'))
                continue
            if symbol['uuid'] not in component['uuids']:
                raise ValueError(f'symbol/netlist identity mismatch: {symbol["id"]} ({ref})')
            seen.add(ref)
            symbol['electrical'] = ref
            for pin in symbol['pins']:
                pin['net'] = by_pin.get((ref, pin['number']))
                pin['library_electrical_type'] = pin['electrical_type']
                metadata = pin_metadata.get((ref, pin['number']), {})
                pin['electrical_type'] = metadata.get('pintype')
                pin['function'] = metadata.get('pinfunction')
                if pin['net'] is None:
                    coverage.append(dict(sheet=sheet['id'], object=pin['id'], reason='pin-not-exported'))
    for ref in components.keys() - seen:
        coverage.append(dict(sheet=components[ref]['sheet'], object=ref, reason='component-not-drawn'))
    return dict(schema=1, source=str(root), electrical_authority='KiCad XML netlist',
                tool=xml.findtext('design/tool'), components=list(components.values()),
                nets=nets, sheets=sheets, erc=erc_data, coverage=coverage)
