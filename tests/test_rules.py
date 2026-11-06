import unittest

from ember_schematic.rules import check_electrical


def model():
    return dict(components=[{'reference': r} for r in ('U1', 'C7')], nets=[
        dict(id='1', name='VCC', nodes=[dict(reference='U1', pin='1'), dict(reference='C7', pin='1')]),
        dict(id='2', name='GND', nodes=[dict(reference='C7', pin='2')])])


class RuleTests(unittest.TestCase):
    def test_overvoltage_requires_declared_rating(self):
        facts = {'rails': [{'net': 'VCC', 'voltage': 5}],
                 'pin_limits': [{'id': 'vdd', 'reference': 'U1', 'pin': '1', 'min': 0, 'max': 3.6}]}
        result = check_electrical(model(), facts)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'violation')
        self.assertEqual(result[0]['fact'], 'vdd')
        self.assertEqual(result[0]['measurements']['voltage'], 5)
        facts['rails'][0]['voltage'] = 3.3
        self.assertEqual(check_electrical(model(), facts)[0]['status'], 'pass')
        del facts['pin_limits'][0]['max']
        self.assertEqual(check_electrical(model(), facts)[0]['status'], 'unknown')

    def test_required_connection_is_explicit_not_reference_heuristic(self):
        facts = {'connections': [{'id': 'bypass', 'kind': 'decoupling', 'component': 'C7',
                                  'pins': ['1', '2'], 'between': ['VCC', 'GND']}]}
        result = check_electrical(model(), facts)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'pass')
        wrong = model()
        wrong['nets'][1]['nodes'][0]['pin'] = '3'
        self.assertEqual(check_electrical(wrong, facts)[0]['status'], 'violation')
        facts['connections'][0]['component'] = None
        self.assertEqual(check_electrical(model(), facts)[0]['status'], 'unknown')

    def test_ambiguous_voltage_and_missing_facts_are_unknown(self):
        self.assertEqual(check_electrical(model(), {}), [])
        facts = {'rails': [{'net': 'VCC', 'voltage': 3.3}, {'net': 'VCC', 'voltage': 5}],
                 'pin_limits': [{'id': 'vdd', 'reference': 'U1', 'pin': '1', 'min': 0, 'max': 3.6}]}
        result = check_electrical(model(), facts)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'unknown')

    def test_invalid_facts_do_not_produce_a_clean_report(self):
        for facts in [{'pin_limit': []}, {'rails': [{'net': 'VCC', 'voltage': float('nan')}]},
                      {'pin_limits': [{'id': 'x', 'reference': 'U1', 'pin': '1', 'min': 5, 'max': 3}]}]:
            with self.subTest(facts=facts), self.assertRaises(ValueError):
                check_electrical(model(), facts)
