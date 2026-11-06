"""Adapt KiUtils objects; KiCad remains the electrical connectivity authority."""
from dataclasses import asdict
import hashlib
from pathlib import Path

from kiutils.schematic import Schematic
from kiutils.utils.sexpr import parse_sexp


def xy(position):
    return [round(float(position.X), 6), round(float(position.Y), 6)]


def transform(point, at, angle, mirror=None):
    """Library coordinates have Y up. Rotate, then mirror in sheet coordinates.

    Matches KiCad's schematic parser and SCH_SYMBOL::SetOrientation matrices.
    """
    x, y = point[0], -point[1]
    rotations = {0: (x, y), 90: (y, -x), 180: (-x, -y), 270: (-y, x)}
    if angle not in rotations or mirror not in (None, 'x', 'y'):
        raise ValueError('unsupported symbol transform')
    x, y = rotations[angle]
    if mirror == 'x':
        y = -y
    elif mirror == 'y':
        x = -x
    return [round(at[0] + x, 6), round(at[1] + y, 6)]


def children(node, name):
    return [v for v in node[1:] if isinstance(v, list) and v and v[0] == name]


def value(node, name, default=None):
    items = children(node, name)
    return items[0][1] if items and len(items[0]) > 1 else default


def read_drawing(root):
    root = Path(root).resolve()
    cache, sheets, coverage = {}, [], []
    known = set('version generator generator_version uuid paper title_block lib_symbols '
                'junction no_connect bus_entry bus_alias wire bus polyline arc circle rectangle '
                'image text text_box label global_label hierarchical_label netclass_flag symbol '
                'sheet sheet_instances symbol_instances'.split())

    def load(path):
        if path not in cache:
            data = path.read_bytes()
            tree = parse_sexp(data.decode('utf-8'))
            cache[path] = (Schematic.from_sexpr(tree), tree, hashlib.sha256(data).hexdigest())
        return cache[path]

    root_uuid = load(root)[0].uuid
    if not root_uuid:
        raise ValueError('root schematic has no UUID')

    def visit(path, instance, name, ancestors):
        if path in ancestors:
            raise ValueError(f'recursive sheet reference: {path}')
        sch, tree, digest = load(path)
        sheet = dict(id=instance, file=str(path), name=name, uuid=sch.uuid,
                     sha256=digest, symbols=[], wires=[], buses=[], labels=[],
                     junctions=[], no_connects=[], bus_entries=[], sheet_pins=[],
                     decorations=[])
        sheets.append(sheet)

        def unknown(reason, obj=None):
            coverage.append(dict(sheet=instance, object=obj, reason=reason))

        def item(obj):
            return dict(id=instance + str(obj.uuid), uuid=obj.uuid, at=xy(obj.position))

        for token in tree[1:]:
            if isinstance(token, list) and token and token[0] not in known:
                unknown('unsupported:' + str(token[0]), value(token, 'uuid'))
        for obj in sch.junctions:
            sheet['junctions'].append(dict(item(obj), diameter=obj.diameter))
        for obj in sch.noConnects:
            sheet['no_connects'].append(item(obj))
        for obj in sch.busEntries:
            sheet['bus_entries'].append(dict(item(obj), size=asdict(obj.size)))
        for obj in sch.graphicalItems:
            if getattr(obj, 'type', None) in ('wire', 'bus'):
                target = sheet['wires'] if obj.type == 'wire' else sheet['buses']
                target.append(dict(id=instance + str(obj.uuid), uuid=obj.uuid,
                                   points=[xy(p) for p in obj.points]))
            else:
                sheet['decorations'].append(dict(kind=type(obj).__name__, data=asdict(obj)))
        for kind, objects in [('local', sch.labels), ('global', sch.globalLabels),
                              ('hierarchical', sch.hierarchicalLabels)]:
            for obj in objects:
                sheet['labels'].append(dict(item(obj), kind=kind, text=obj.text,
                                            angle=obj.position.angle or 0))
        for obj in sch.texts + sch.textBoxes + sch.shapes + sch.images + sch.netclassFlags:
            sheet['decorations'].append(dict(kind=type(obj).__name__, data=asdict(obj)))
        libs = {lib.libId: lib for lib in sch.libSymbols}
        raw_symbols = {value(raw, 'uuid'): raw for raw in children(tree, 'symbol')}
        full_path = '/' + root_uuid + instance.rstrip('/')
        for obj in sch.schematicSymbols:
            properties = {p.key: p.value for p in obj.properties}
            matches = [p for project in obj.instances for p in project.paths
                       if p.sheetInstancePath.rstrip('/') == full_path]
            identities = {(p.reference, p.unit) for p in matches}
            if len(identities) > 1:
                raise ValueError(f'ambiguous symbol identity: {instance}{obj.uuid}')
            reference, unit = next(iter(identities), (properties.get('Reference'), obj.unit or 1))
            if not identities:
                unknown('missing-instance-reference', obj.uuid)
            symbol = dict(item(obj), sheet=instance, reference=reference, unit=unit,
                          lib_id=obj.libId, fields=properties, angle=obj.position.angle or 0,
                          mirror=obj.mirror, dnp=obj.dnp, in_bom=obj.inBom,
                          pins=[], body=[], electrical=None)
            sheet['symbols'].append(symbol)
            lib = libs.get(obj.libName or obj.libId)
            if lib is None or lib.extends:
                unknown('unresolved-symbol-definition', obj.uuid)
                continue
            raw = raw_symbols[obj.uuid]
            style = value(raw, 'body_style', value(raw, 'convert', 1))
            definitions = [lib] + [u for u in lib.units if u.unitId in (0, unit)
                                  and u.styleId in (0, style)]
            for definition in definitions:
                for graphic in definition.graphicItems:
                    symbol['body'].append(dict(kind=type(graphic).__name__, data=asdict(graphic)))
                for pin in definition.pins:
                    at = transform(xy(pin.position), symbol['at'], symbol['angle'], obj.mirror)
                    symbol['pins'].append(dict(
                        id=symbol['id'] + ':' + str(unit) + ':' + pin.number,
                        uuid=obj.pins.get(pin.number), number=pin.number, name=pin.name,
                        electrical_type=pin.electricalType, at=at, local=xy(pin.position),
                        angle=pin.position.angle or 0, length=pin.length, hidden=pin.hide,
                        no_connect=any(n['at'] == at for n in sheet['no_connects']), net=None))
        for child in sch.sheets:
            for pin in child.pins:
                sheet['sheet_pins'].append(dict(item(pin), name=pin.name,
                                                child=instance + child.uuid + '/'))
            child_name = child.fileName.value
            if not child_name or '${' in child_name:
                unknown('unresolved-sheet-file', child.uuid)
                continue
            visit((path.parent / child_name).resolve(), instance + child.uuid + '/',
                  name.rstrip('/') + '/' + child.sheetName.value + '/', ancestors + [path])

    visit(root, '/', '/', [])
    return sheets, coverage
