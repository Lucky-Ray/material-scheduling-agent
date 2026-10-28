import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from agent import ROOT, Tools, MockModel, run


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'data/catalog.json').read_text(encoding='utf-8'))
        self.tools = Tools(self.data, ':memory:')
        self.req = {'material_id': 'M01', 'requested_slot': self.data['slots'][1], 'hard_time': True}

    def tearDown(self):
        self.tools.conn.close()

    def go(self, **kw):
        return run(dict(self.req, **kw), self.tools, MockModel())

    def test_normal_and_duplicate(self):
        a, b = self.go(), self.go()
        self.assertEqual(a['status'], 'completed')
        self.assertEqual(b['draft']['draft_id'], a['draft']['draft_id'])
        self.assertTrue(b['draft']['duplicate'])
        self.assertEqual(self.tools.conn.execute('SELECT COUNT(*) FROM drafts').fetchone()[0], 1)

    def test_flexible_conflict(self):
        r = self.go(requested_slot=self.data['slots'][0], hard_time=False)
        self.assertEqual(r['status'], 'needs_confirmation')
        self.assertEqual(r['draft']['confirmation'], 'pending')
        self.assertEqual(r['draft']['slot'], self.data['slots'][1])
        self.assertFalse(r['published'])

    def test_hard_conflict(self):
        r = self.go(requested_slot=self.data['slots'][0])
        self.assertEqual(r['status'], 'needs_confirmation')
        self.assertIsNone(r['draft'])

    def test_missing_and_risk(self):
        for mid in ('UNKNOWN', 'M02', 'M03'):
            with self.subTest(mid=mid):
                self.assertEqual(self.go(material_id=mid)['status'], 'blocked')
        self.assertEqual(self.tools.conn.execute('SELECT COUNT(*) FROM drafts').fetchone()[0], 0)

    def test_missing_time(self):
        self.assertEqual(self.go(requested_slot=None)['status'], 'blocked')

    def test_save_failure(self):
        self.tools.fail_save = True
        r = self.go()
        self.assertEqual(r['status'], 'failed')
        self.assertFalse(r['draft']['ok'])

    def test_tools_enforce_boundaries(self):
        r = self.tools.call('save_draft', {'slot': self.data['slots'][2]}, self.req)
        self.assertEqual(r['error'], 'hard_time_requires_user_confirmation')
        self.assertTrue(self.go()['draft']['ok'])
        other = dict(self.req, material_id='M04')
        self.data['materials']['M04'] = self.data['materials']['M01']
        self.assertEqual(self.tools.call('save_draft', {'slot': self.req['requested_slot']}, other)['error'], 'slot_conflict')

    def test_limit_and_false_success(self):
        class Bad:
            def choose(self, request, trace):
                return {'finish': True, 'status': 'completed'}
        self.assertEqual(run(self.req, self.tools, Bad())['status'], 'failed')
        self.assertEqual(run(self.req, self.tools, MockModel(), 1)['status'], 'incomplete')

    def test_prerequisites(self):
        class Skip:
            def choose(self, request, trace):
                return {'tool': 'save_draft', 'args': {'slot': self.req['requested_slot']}}
        model = Skip()
        model.req = self.req
        r = run(self.req, self.tools, model, 1)
        self.assertEqual(r['trace'][0]['result']['error'], 'prerequisites_not_observed')


if __name__ == '__main__':
    unittest.main()
