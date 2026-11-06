import unittest

from ember_schematic.wires import build_graph, analyze_wires


def sheet(segments, junctions=(), labels=()):
    return dict(id='/', wires=[dict(id=f'/w{i}', points=[list(a), list(b)])
                               for i, (a, b) in enumerate(segments)],
                junctions=[dict(id=f'/j{i}', at=list(p)) for i, p in enumerate(junctions)],
                labels=[dict(id=f'/l{i}', at=list(p), text='same') for i, p in enumerate(labels)],
                symbols=[], sheet_pins=[], no_connects=[])


class WireTests(unittest.TestCase):
    def test_crossing_needs_contact(self):
        segments = [((-2, 0), (2, 0)), ((0, -2), (0, 2))]
        plain = build_graph(sheet(segments))
        joined = build_graph(sheet(segments, junctions=[(0, 0)]))
        self.assertIn('nodes', plain)
        self.assertEqual((len(plain['nodes']), len(plain['edges'])), (4, 2))
        self.assertEqual((len(joined['nodes']), len(joined['edges'])), (5, 4))

    def test_branch_and_virtual_labels_are_not_cycles(self):
        s = sheet([((0, 0), (10, 0)), ((5, 0), (5, 5)), ((20, 0), (30, 0))],
                  labels=[(0, 0), (30, 0)])
        graph = build_graph(s)
        self.assertIn('edges', graph)
        self.assertEqual(len(graph['edges']), 4)
        self.assertEqual(analyze_wires({'sheets': [s]}), [])

    def test_square_cycle_has_source_evidence(self):
        s = sheet([((0, 0), (10, 0)), ((10, 0), (10, 10)),
                   ((10, 10), (0, 10)), ((0, 10), (0, 0))])
        findings = analyze_wires({'sheets': [s]})
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding['rule'], 'wire-cycle')
        self.assertEqual(set(finding['objects']), {'/w0', '/w1', '/w2', '/w3'})
        self.assertEqual(finding['measurements']['perimeter_mm'], 40)
        self.assertEqual(finding['status'], 'candidate')

    def test_overlapping_segments_are_duplicates_not_cycles(self):
        s = sheet([((0, 0), (10, 0)), ((8, 0), (2, 0))])
        findings = analyze_wires({'sheets': [s]})
        self.assertEqual([x['rule'] for x in findings], ['duplicate-wire'])
        self.assertEqual(findings[0]['measurements']['overlap_mm'], 6)

    def test_detour_is_measured_between_anchors(self):
        s = sheet([((0, 0), (0, 10)), ((0, 10), (10, 10)), ((10, 10), (10, 0))])
        findings = analyze_wires({'sheets': [s]})
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['rule'], 'wire-detour')
        self.assertEqual(findings[0]['measurements'],
                         dict(length_mm=30, lower_bound_mm=10, bends=2, metric='manhattan'))

    def test_attached_pin_and_label_are_anchors_without_new_wires(self):
        s = sheet([((0, 0), (10, 0))], labels=[(2, 0)])
        s['symbols'] = [dict(pins=[dict(id='pin', at=[7, 0])])]
        graph = build_graph(s)
        self.assertIn('nodes', graph)
        self.assertEqual(len(graph['edges']), 3)
        self.assertEqual({a for n in graph['nodes'] for a in n['anchors']}, {'/l0', 'pin'})

    def test_hidden_pin_does_not_join_a_plain_crossing(self):
        s = sheet([((-2, 0), (2, 0)), ((0, -2), (0, 2))])
        s['symbols'] = [dict(pins=[dict(id='hidden', at=[0, 0], hidden=True)])]
        graph = build_graph(s)
        self.assertEqual(len(graph['edges']), 2)
