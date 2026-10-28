import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from agent import ROOT, Tools, MockModel, run


class HardeningTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'data/catalog.json').read_text(encoding='utf-8'))
        self.tools = Tools(copy.deepcopy(self.data), ':memory:')
        self.req = {'material_id': 'M01', 'requested_slot': self.data['slots'][0], 'hard_time': False}

    def tearDown(self):
        self.tools.conn.close()

    def test_request_idempotency_even_when_model_changes_slot(self):
        a = self.tools.call('save_draft', {'slot': self.data['slots'][1]}, self.req)
        b = self.tools.call('save_draft', {'slot': self.data['slots'][2]}, self.req)
        self.assertEqual(a['draft_id'], b['draft_id'])
        self.assertEqual(b['slot'], self.data['slots'][1])
        self.assertTrue(b['duplicate'])
        self.assertEqual(self.tools.conn.execute('SELECT COUNT(*) FROM drafts').fetchone()[0], 1)

    def test_rules_rechecked_on_replay(self):
        self.tools.call('save_draft', {'slot': self.data['slots'][1]}, self.req)
        self.tools.data['materials']['M01']['tags'] = ['unverified_claim']
        result = self.tools.call('save_draft', {'slot': self.data['slots'][1]}, self.req)
        self.assertFalse(result['ok'])
        self.assertEqual(result['risks'], ['unverified_claim'])

    def test_request_id_cannot_be_reused_for_other_material(self):
        req = dict(self.req, request_id='request-1')
        self.tools.call('save_draft', {'slot': self.data['slots'][1]}, req)
        self.tools.data['materials']['M04'] = self.tools.data['materials']['M01']
        result = self.tools.call('save_draft', {'slot': self.data['slots'][2]}, dict(req, material_id='M04'))
        self.assertEqual(result['error'], 'request_id_conflict')

    def test_replay_cannot_bypass_new_hard_constraint(self):
        self.tools.call('save_draft', {'slot': self.data['slots'][1]}, self.req)
        result = self.tools.call('save_draft', {'slot': self.data['slots'][1]}, dict(self.req, hard_time=True))
        self.assertEqual(result['error'], 'hard_time_requires_user_confirmation')

    def test_invalid_input_and_model_protocol(self):
        for request in ([], dict(self.req, hard_time='false'), dict(self.req, material_id=3)):
            self.assertEqual(run(request, self.tools, MockModel())['status'], 'failed')
        class BadModel:
            def __init__(self, action): self.action = action
            def choose(self, request, trace): return self.action
        for action in ([], {'finish': 'true', 'status': 'completed'}, {'finish': True, 'status': 'published'}, {'tool': 'save_draft', 'args': []}):
            self.assertEqual(run(self.req, self.tools, BadModel(action))['status'], 'failed')

    def test_structured_material_summary(self):
        result = run(self.req, self.tools, MockModel())
        summary = result['material_result']
        self.assertEqual(summary['review_status'], 'passed')
        self.assertEqual(summary['save_status'], 'saved')
        self.assertEqual(summary['suggested_slot'], self.data['slots'][1])
        self.assertIn('confirm_alternative_time', summary['pending_items'])

    def test_saved_side_effect_survives_execution_limit(self):
        result = run(self.req, self.tools, MockModel(), max_steps=4)
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['material_result']['save_status'], 'saved')
        self.assertTrue(result['draft']['ok'])

    def test_cli_missing_file_returns_json_and_nonzero(self):
        r = subprocess.run([sys.executable, str(ROOT / 'src/agent.py'), '--input', str(ROOT / 'missing-file.json')], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 1)
        self.assertEqual(json.loads(r.stdout)['reason'], 'FileNotFoundError')
        self.assertNotIn('Traceback', r.stderr)

    def test_cli_catalog_override(self):
        r = subprocess.run([sys.executable, str(ROOT / 'src/agent.py'), '--input', str(ROOT / 'examples/changed_occupied.input.json'), '--catalog', str(ROOT / 'examples/changed_occupied.catalog.json'), '--db', ':memory:'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)['draft']['slot'], self.data['slots'][0])

    def test_legacy_database_migration(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / 'legacy.sqlite3'
            conn = sqlite3.connect(db)
            conn.execute('CREATE TABLE drafts (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
            payload = dict(self.req, slot=self.data['slots'][1], confirmation='pending')
            conn.execute('INSERT INTO drafts VALUES (?,?)', ('old-id', json.dumps(payload)))
            conn.commit()
            conn.close()
            tools = Tools(self.data, db)
            try:
                result = tools.call('save_draft', {'slot': self.data['slots'][2]}, self.req)
                self.assertEqual(result['draft_id'], 'old-id')
                self.assertTrue(result['duplicate'])
            finally:
                tools.conn.close()


if __name__ == '__main__': unittest.main()
