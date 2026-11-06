"""Physical wire sections, cycle candidates and measured drawing detours.

No edges are created from net membership, labels, or through components.
"""
from collections import defaultdict, deque
from math import dist


def on_segment(p, a, b):
    return (min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
            and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])
            and abs((b[0]-a[0])*(p[1]-a[1]) - (b[1]-a[1])*(p[0]-a[0])) < 1e-9)


def build_graph(sheet):
    anchors, points, segments = defaultdict(list), set(), []
    for obj in sheet.get('junctions', []) + sheet.get('labels', []) + sheet.get('sheet_pins', []):
        anchors[tuple(obj['at'])].append(obj['id'])
    for symbol in sheet.get('symbols', []):
        for pin in symbol['pins']:
            if not pin.get('hidden', False):
                anchors[tuple(pin['at'])].append(pin['id'])
    points.update(anchors)
    for wire in sheet['wires']:
        for a, b in zip(wire['points'], wire['points'][1:]):
            a, b = tuple(a), tuple(b)
            if a != b:
                segments.append((a, b, wire['id']))
                points.update((a, b))
    coords = sorted(points)
    node_ids = {p: i for i, p in enumerate(coords)}
    nodes = [dict(id=i, at=list(p), anchors=sorted(anchors[p])) for i, p in enumerate(coords)]
    sections = defaultdict(list)
    for a, b, source in segments:
        contacts = sorted((p for p in coords if on_segment(p, a, b)),
                          key=lambda p: (p[0]-a[0])**2 + (p[1]-a[1])**2)
        for start, end in zip(contacts, contacts[1:]):
            key = tuple(sorted((node_ids[start], node_ids[end])))
            sections[key].append(source)
    edges = [dict(id=i, start=a, end=b, sources=sources,
                  length_mm=round(dist(coords[a], coords[b]), 6))
             for i, ((a, b), sources) in enumerate(sorted(sections.items()))]
    return dict(nodes=nodes, edges=edges)


def adjacency(graph):
    adj = defaultdict(list)
    for edge in graph['edges']:
        adj[edge['start']].append((edge['end'], edge['id']))
        adj[edge['end']].append((edge['start'], edge['id']))
    return adj


def cycle_basis(graph):
    """Fundamental cycles of a deterministic spanning forest, not all cycles."""
    parents = list(range(len(graph['nodes'])))
    tree = defaultdict(list)

    def root(v):
        while parents[v] != v:
            parents[v] = parents[parents[v]]
            v = parents[v]
        return v

    for e in graph['edges']:
        a, b = e['start'], e['end']
        ra, rb = root(a), root(b)
        if ra != rb:
            parents[ra] = rb
            tree[a].append((b, e['id']))
            tree[b].append((a, e['id']))
            continue
        queue, previous = deque([a]), {a: None}
        while b not in previous:
            v = queue.popleft()
            for w, edge in tree[v]:
                if w not in previous:
                    previous[w] = (v, edge)
                    queue.append(w)
        vertices, edges, v = [b], [e['id']], b
        while v != a:
            v, edge = previous[v]
            vertices.append(v)
            edges.append(edge)
        yield vertices + [b], edges


def chains(graph):
    adj, used = adjacency(graph), set()
    stops = {n['id'] for n in graph['nodes'] if n['anchors'] or len(adj[n['id']]) != 2}
    for start in sorted(stops):
        for nxt, edge in adj[start]:
            if edge in used:
                continue
            vertices, edges = [start, nxt], [edge]
            used.add(edge)
            while nxt not in stops:
                nxt, edge = next((v, e) for v, e in adj[nxt] if e != edge)
                vertices.append(nxt)
                edges.append(edge)
                used.add(edge)
            yield vertices, edges


def finding(rule, sheet, graph, vertices, edges, measurements):
    return dict(rule=rule, status='candidate', severity='note', sheet=sheet,
                objects=sorted({s for e in edges for s in graph['edges'][e]['sources']}),
                geometry=[graph['nodes'][v]['at'] for v in vertices], measurements=measurements)


def analyze_wires(model):
    findings = []
    for sheet in model['sheets']:
        graph = build_graph(sheet)
        sheet['wire_graph'] = graph
        for edge in graph['edges']:
            if len(edge['sources']) > 1:
                findings.append(finding('duplicate-wire', sheet['id'], graph,
                                        [edge['start'], edge['end']], [edge['id']],
                                        dict(overlap_mm=edge['length_mm'])))
        for vertices, edges in cycle_basis(graph):
            findings.append(finding('wire-cycle', sheet['id'], graph, vertices, edges,
                                    dict(perimeter_mm=round(sum(graph['edges'][e]['length_mm'] for e in edges), 6))))
        for vertices, edges in chains(graph):
            if vertices[0] == vertices[-1]:
                continue
            pts = [graph['nodes'][v]['at'] for v in vertices]
            vectors = [(b[0]-a[0], b[1]-a[1]) for a, b in zip(pts, pts[1:])]
            bends = sum(abs(a[0]*b[1] - a[1]*b[0]) > 1e-9 or a[0]*b[0]+a[1]*b[1] < 0
                        for a, b in zip(vectors, vectors[1:]))
            orthogonal = all(x == 0 or y == 0 for x, y in vectors)
            lower = (abs(pts[-1][0]-pts[0][0]) + abs(pts[-1][1]-pts[0][1])
                     if orthogonal else dist(pts[0], pts[-1]))
            length = sum(graph['edges'][e]['length_mm'] for e in edges)
            minimum_bends = int(pts[0][0] != pts[-1][0] and pts[0][1] != pts[-1][1]) if orthogonal else 0
            if length > lower + 1e-6 or bends > minimum_bends:
                findings.append(finding('wire-detour', sheet['id'], graph, vertices, edges,
                                        dict(length_mm=round(length, 6), lower_bound_mm=round(lower, 6),
                                             bends=bends, metric='manhattan' if orthogonal else 'euclidean')))
    return findings
