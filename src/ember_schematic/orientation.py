"""Rotation costs are measurements; text/obstacle clearance is not yet proven."""
from collections import defaultdict

from .drawing import transform
from .wires import build_graph, chains


def suggest_orientations(model):
    results = []
    for sheet in model['sheets']:
        graph = sheet.get('wire_graph') or build_graph(sheet)
        ends = defaultdict(list)
        for vertices, _ in chains(graph):
            if vertices[0] != vertices[-1]:
                for start, end in ((vertices[0], vertices[-1]), (vertices[-1], vertices[0])):
                    for anchor in graph['nodes'][start]['anchors']:
                        ends[anchor].append(graph['nodes'][end])
        for symbol in sheet['symbols']:
            result = dict(rule='symbol-orientation', status='unknown', severity='note',
                          sheet=sheet['id'], objects=[symbol['id']], geometry=[symbol['at']],
                          reason='pin routes are missing, branched or ambiguous', measurements={})
            pins = [p for p in symbol['pins'] if not p.get('hidden') and not p.get('no_connect')]
            own = {p['id'] for p in pins}
            if pins and all(len(ends[p['id']]) == 1 and 'local' in p and
                            not own.intersection(ends[p['id']][0]['anchors']) for p in pins):
                costs = {}
                for angle in (0, 90, 180, 270):
                    cost = 0
                    for pin in pins:
                        at = transform(pin['local'], symbol['at'], angle, symbol['mirror'])
                        far = ends[pin['id']][0]['at']
                        cost += abs(at[0]-far[0]) + abs(at[1]-far[1])
                    costs[str(angle)] = round(cost, 6)
                result.update(measurements=dict(quarter_turns=costs, unit='mm', metric='manhattan-lower-bound'),
                              reason='pin displacement measured; symbol/text clearance and rerouting are unverified')
            results.append(result)
    return results
