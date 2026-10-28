"""Reproduce offline evidence; every scenario gets an isolated database."""
import copy
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from agent import ROOT, Tools, MockModel, run

base = json.loads((ROOT / 'data/catalog.json').read_text(encoding='utf-8'))
normal = {'material_id': 'M01', 'requested_slot': base['slots'][1], 'hard_time': True}
cases = {
    'normal': (normal, 'completed'),
    'conflict': (dict(normal, requested_slot=base['slots'][0], hard_time=False), 'needs_confirmation'),
    'missing': (dict(normal, material_id='UNKNOWN'), 'blocked'),
    'missing_metadata': (dict(normal, material_id='M03'), 'blocked'),
    'risk': (dict(normal, material_id='M02'), 'blocked'),
    'save_failure': (normal, 'failed'),
    'hard_conflict': (dict(normal, requested_slot=base['slots'][0]), 'needs_confirmation'),
    'duplicate': (normal, 'completed'),
    'no_slots': (dict(normal, hard_time=False), 'blocked'),
    'changed_occupied': (dict(normal, requested_slot=base['slots'][0], hard_time=False), 'completed'),
    'changed_rule': (normal, 'blocked'),
    'step_limit': (normal, 'incomplete'),
}
report = []
for name, (request, expected) in cases.items():
    data = copy.deepcopy(base)
    if name == 'no_slots':
        data['occupied'] = list(data['slots'])
    elif name == 'changed_occupied':
        data['occupied'] = []
    elif name == 'changed_rule':
        data['materials']['M01']['tags'] = ['unverified_claim']
    tools = Tools(data, ':memory:', fail_save=name == 'save_failure')
    first = run(request, tools, MockModel(), 1 if name == 'step_limit' else 10)
    result = run(request, tools, MockModel()) if name == 'duplicate' else first
    count = tools.conn.execute('SELECT COUNT(*) FROM drafts').fetchone()[0]
    result['mode'] = 'mock'
    assert result['status'] == expected, (name, result)
    if name == 'duplicate':
        assert count == 1 and result['draft']['duplicate']
        assert first['draft']['draft_id'] == result['draft']['draft_id']
    if name == 'conflict':
        assert result['draft']['slot'] == base['slots'][1]
        assert result['draft']['confirmation'] == 'pending'
    if name in ('missing', 'missing_metadata', 'risk', 'save_failure', 'hard_conflict', 'no_slots', 'changed_rule', 'step_limit'):
        assert count == 0
    for suffix, value in [('input', request), ('catalog', data), ('trace', result)]:
        (ROOT / 'examples' / f'{name}.{suffix}.json').write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    if name == 'duplicate':
        first['mode'] = 'mock'
        (ROOT / 'examples/duplicate.first.trace.json').write_text(json.dumps(first, ensure_ascii=False, indent=2), encoding='utf-8')
    report.append({'case': name, 'expected': expected, 'actual': result['status'], 'passed': True, 'draft_count': count, 'tool_path': [t['tool'] for t in result['trace']]})
    tools.conn.close()
    print(name, result['status'])
(ROOT / 'examples/scenario-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
