"""Bounded checks against explicit project facts, never guessed part ratings."""
from collections import defaultdict
from math import isfinite


def validate_facts(facts):
    allowed = dict(rails={'id', 'net', 'voltage'},
                   pin_limits={'id', 'reference', 'pin', 'min', 'max'},
                   connections={'id', 'kind', 'component', 'pins', 'between'})
    if not isinstance(facts, dict) or facts.keys() - allowed.keys():
        raise ValueError('constraints must contain only rails, pin_limits and connections')
    for group, entries in facts.items():
        if not isinstance(entries, list):
            raise ValueError(f'{group} must be a list')
        for entry in entries:
            if not isinstance(entry, dict) or entry.keys() - allowed[group]:
                raise ValueError(f'unknown or invalid {group} fields')
            for key, v in entry.items():
                if v is None:
                    continue
                if key in ('voltage', 'min', 'max'):
                    if isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v):
                        raise ValueError(f'{key} must be a finite number')
                elif key in ('pins', 'between'):
                    if not isinstance(v, list) or len(v) != 2 or not all(isinstance(p, str) and p for p in v):
                        raise ValueError(f'{key} must contain two nonempty strings')
                elif not isinstance(v, str):
                    raise ValueError(f'{key} must be a string')
            if entry.get('min') is not None and entry.get('max') is not None and entry['min'] > entry['max']:
                raise ValueError('pin minimum exceeds maximum')
            if group == 'connections' and entry.get('kind') not in ('pull-up', 'decoupling'):
                raise ValueError('connection kind must be pull-up or decoupling')


def check_electrical(model, facts):
    validate_facts(facts)
    by_name, by_pin, voltages = defaultdict(list), {}, defaultdict(set)
    components = {c['reference'] for c in model['components']}
    for net in model['nets']:
        by_name[net['name']].append(net['id'])
        for node in net['nodes']:
            by_pin[node['reference'], node['pin']] = net['id']
    for rail in facts.get('rails', []):
        if len(by_name[rail.get('net')]) == 1 and rail.get('voltage') is not None:
            voltages[by_name[rail['net']][0]].add(rail['voltage'])
    findings = []
    for i, limit in enumerate(facts.get('pin_limits', [])):
        ref, pin = limit.get('reference'), limit.get('pin')
        net = by_pin.get((ref, pin))
        values = voltages[net]
        result = dict(rule='pin-voltage', fact=limit.get('id', f'pin_limits/{i}'),
                      status='unknown', severity='note', objects=[ref, pin], net=net,
                      measurements={}, reason='missing or ambiguous voltage/rating')
        if len(values) == 1 and limit.get('min') is not None and limit.get('max') is not None:
            voltage = next(iter(values))
            valid = limit['min'] <= voltage <= limit['max']
            result.update(status='pass' if valid else 'violation', severity='note' if valid else 'error',
                          reason='declared voltage compared with declared pin limits',
                          measurements=dict(voltage=voltage, minimum=limit['min'], maximum=limit['max']))
        findings.append(result)
    for i, constraint in enumerate(facts.get('connections', [])):
        ref, pins, names = constraint.get('component'), constraint.get('pins'), constraint.get('between')
        result = dict(rule='required-connection', fact=constraint.get('id', f'connections/{i}'),
                      kind=constraint['kind'], objects=[ref], status='unknown', severity='note',
                      reason='component, pin or net identity is incomplete', measurements={})
        if ref and pins and names and all(len(by_name[n]) == 1 for n in names):
            expected = sorted(by_name[n][0] for n in names)
            actual = [by_pin.get((ref, pin)) for pin in pins]
            valid = ref in components and None not in actual and sorted(actual) == expected
            result.update(status='pass' if valid else 'violation', severity='note' if valid else 'error',
                          reason='only the declared two-pin connection is checked',
                          measurements=dict(expected_nets=expected, actual_nets=actual))
        findings.append(result)
    return findings
