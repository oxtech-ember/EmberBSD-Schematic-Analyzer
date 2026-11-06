"""Self-contained, escaped HTML and SVG wire-graph evidence."""
from collections import Counter
from html import escape
import json
import os
from pathlib import Path
import tempfile


def write_text(path, text):
    """Replace an output file, never follow an existing file symlink."""
    staged = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.schematic-', delete=False) as stream:
            staged = Path(stream.name)
            stream.write(text)
        os.replace(staged, path)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


def sheet_svg(sheet, findings):
    locations = [p for w in sheet['wires'] for p in w['points']]
    locations += [s['at'] for s in sheet['symbols']] + [l['at'] for l in sheet['labels']]
    locations += [p['at'] for s in sheet['symbols'] for p in s['pins']]
    locations = locations or [[0, 0], [40, 30]]
    x0, y0 = min(p[0] for p in locations)-8, min(p[1] for p in locations)-8
    x1, y1 = max(p[0] for p in locations)+15, max(p[1] for p in locations)+8
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1-x0} {y1-y0}" role="img">',
           f'<title>{escape(sheet["name"])} — schematic wire graph</title>',
           '<style>text{font:1.8px sans-serif;fill:#27343c}.wire{fill:none;stroke:#367a71;stroke-width:.3}'
           '.candidate{stroke:#d95125;stroke-width:.7}.pin{fill:white;stroke:#476985;stroke-width:.25}'
           '.symbol{fill:#edf3f7;stroke:#476985;stroke-width:.25}</style>']
    highlighted = {obj for f in findings if f.get('sheet') == sheet['id'] for obj in f['objects']}
    for wire in sheet['wires']:
        points = ' '.join(f'{x},{y}' for x, y in wire['points'])
        cls = 'wire candidate' if wire['id'] in highlighted else 'wire'
        out.append(f'<polyline class="{cls}" points="{points}"><title>{escape(wire["id"])}</title></polyline>')
    for obj in sheet['junctions']:
        x, y = obj['at']
        out.append(f'<circle cx="{x}" cy="{y}" r=".6" fill="#367a71"/>')
    for obj in sheet['no_connects']:
        x, y = obj['at']
        out.append(f'<path d="M{x-.5},{y-.5}l1,1m0,-1l-1,1" stroke="#6b8192" stroke-width=".2"/>')
    for symbol in sheet['symbols']:
        x, y = symbol['at']
        out.append(f'<rect class="symbol" x="{x-1.3}" y="{y-1.3}" width="2.6" height="2.6">'
                   f'<title>{escape(symbol["id"])}</title></rect>')
        out.append(f'<text x="{x+2}" y="{y-1.5}">{escape(str(symbol["reference"]))}:{symbol["unit"]}</text>')
        for pin in symbol['pins']:
            if pin.get('hidden'):
                continue
            px, py = pin['at']
            out.append(f'<circle class="pin" cx="{px}" cy="{py}" r=".5">'
                       f'<title>{escape(pin["id"])} {escape(pin["name"])}</title></circle>')
    for label in sheet['labels']:
        x, y = label['at']
        out.append(f'<text x="{x+.7}" y="{y-.7}">{escape(label["text"])}</text>')
    out.append('</svg>')
    return ''.join(out)


def write_report(model, report, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name, obj in [('model.json', model), ('report.json', report)]:
        write_text(output / name, json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    findings = report['findings']
    counts = Counter(f['status'] for f in findings)
    html = ['<!doctype html><html lang="en"><meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width,initial-scale=1">',
            '<title>Schematic analysis</title><style>'
            'body{font:16px/1.5 system-ui,sans-serif;margin:2rem auto;padding:0 1rem;max-width:1100px;color:#27343c;background:#f5f7f8}'
            'h1,h2{line-height:1.2}section,article{background:white;border:1px solid #dbe3e8;border-radius:8px;padding:1rem;margin:1rem 0}'
            'svg{width:100%;background:white}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.85rem}'
            'a{color:#246d7c}.meta{color:#526672}li{margin:.5rem 0}.error{border-left:4px solid #c63d20}'
            '</style><h1>Schematic analysis</h1>',
            f'<p>{escape(Path(model["source"]).name)}</p>',
            '<p class="meta">Read-only analysis. Diagrams show wire graphs and pin anchors, not a complete KiCad rendering. '
            'Orange wires are candidates to inspect, not proven electrical errors.</p>',
            f'<p>{len(model["sheets"])} sheet instances · {len(model["components"])} components · '
            f'{len(model["nets"])} nets · {len(model["coverage"])} coverage limitations</p>',
            f'<p>Rule results: {escape(str(dict(counts)))}. Electrical checks: {escape(report["electrical_checks"])}.</p>',
            '<p><a href="model.json">JSON model</a> · <a href="report.json">JSON findings</a></p><nav>']
    indexes = {s['id']: i for i, s in enumerate(model['sheets'], 1)}
    for sheet in model['sheets']:
        i = indexes[sheet['id']]
        html.append(f'<a href="#sheet-{i}">{escape(sheet["name"])}</a> · ')
    html.append('</nav><section><h2>Checks and candidates</h2>')
    for f in findings:
        if f['status'] == 'pass':
            continue
        target = indexes.get(f.get('sheet'))
        link = f'<a href="#sheet-{target}">Locate</a>' if target else ''
        html.append(f'<article class="{escape(f["severity"])}"><b>{escape(f["rule"])} — {escape(f["status"])}</b> {link}'
                    f'<pre>{escape(json.dumps(f, ensure_ascii=False, indent=2))}</pre></article>')
    html.append('</section>')
    for sheet in model['sheets']:
        i = indexes[sheet['id']]
        svg = sheet_svg(sheet, findings)
        filename = f'sheet-{i:03d}.svg'
        write_text(output / filename, svg)
        html.append(f'<section id="sheet-{i}"><h2>{escape(sheet["name"])}</h2>'
                    f'<p class="meta">{escape(sheet["id"])}</p><a href="{filename}">Open SVG to zoom</a>{svg}</section>')
    for title, data in [('Coverage limitations', model['coverage']), ('KiCad ERC', model['erc']),
                        ('Orientation measurements (clearance unverified)', report['orientations'])]:
        html.append(f'<details><summary>{title}</summary><pre>{escape(json.dumps(data, ensure_ascii=False, indent=2))}</pre></details>')
    html.append('</html>')
    write_text(output / 'index.html', ''.join(html))
