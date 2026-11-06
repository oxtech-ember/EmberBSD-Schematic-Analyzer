import unittest

from ember_schematic.orientation import suggest_orientations
from test_wires import sheet


class OrientationTests(unittest.TestCase):
    def test_pin_transform_costs_do_not_claim_collision_free_routing(self):
        s = sheet([((-5, 0), (-5, -10)), ((-5, -10), (0, -10)),
                   ((5, 0), (5, 10)), ((5, 10), (0, 10))])
        s['symbols'] = [dict(id='/u', at=[0, 0], angle=0, mirror=None, pins=[
            dict(id='/u:1', at=[-5, 0], local=[-5, 0], hidden=False),
            dict(id='/u:2', at=[5, 0], local=[5, 0], hidden=False)])]
        result = suggest_orientations({'sheets': [s], 'coverage': []})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'unknown')
        self.assertEqual(result[0]['measurements']['quarter_turns']['270'], 10)
        self.assertNotIn('recommended_angle', result[0])

    def test_disconnected_or_missing_pin_geometry_is_unknown(self):
        s = sheet([])
        s['symbols'] = [dict(id='/u', at=[0, 0], angle=0, mirror=None, pins=[])]
        result = suggest_orientations({'sheets': [s], 'coverage': []})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'unknown')
        self.assertEqual(result[0]['measurements'], {})
