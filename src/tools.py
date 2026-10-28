"""Local business tools and transactional draft storage."""
import hashlib
import json
import sqlite3


class Tools:
    def __init__(self, data, db, fail_save=False):
        self.data = data
        self.fail_save = fail_save
        self.conn = sqlite3.connect(str(db))
        self.conn.execute('CREATE TABLE IF NOT EXISTS drafts (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')

    def call(self, name, args, request):
        mid = request.get('material_id')
        material = self.data['materials'].get(mid)
        if name == 'read_material':
            return {'material': material, 'missing': [] if material else ['material_id or material']}
        if name == 'check_rules':
            if not material:
                return {'ok': False, 'missing': ['material']}
            missing = [k for k in ('title', 'rights') if not material.get(k)]
            risks = [rule for rule in self.data['rules'] if rule in material.get('tags', [])]
            return {'ok': not missing and not risks, 'missing': missing, 'risks': risks}
        if name == 'query_slots':
            occupied = set(self.data['occupied'])
            drafts = [json.loads(row[0]) for row in self.conn.execute('SELECT payload FROM drafts')]
            occupied.update(d['slot'] for d in drafts)
            return {'available': [s for s in self.data['slots'] if s not in occupied],
                    'existing': [d for d in drafts if d['material_id'] == mid and d['requested_slot'] == request.get('requested_slot')],
                    'requested_available': request.get('requested_slot') in self.data['slots'] and request.get('requested_slot') not in occupied}
        if name == 'save_draft':
            slot = args.get('slot')
            payload = {'material_id': mid, 'slot': slot, 'requested_slot': request.get('requested_slot'),
                       'confirmation': 'pending' if slot != request.get('requested_slot') else 'not_required'}
            key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:20]
            old = self.conn.execute('SELECT payload FROM drafts WHERE id=?', (key,)).fetchone()
            if old:
                return {'ok': True, 'draft_id': key, 'duplicate': True, **json.loads(old[0])}
            rules = self.call('check_rules', {}, request)
            if not rules['ok']:
                return {'ok': False, 'error': 'unsafe_or_incomplete', **rules}
            if not request.get('requested_slot'):
                return {'ok': False, 'error': 'missing_requested_slot'}
            if slot != request['requested_slot'] and request.get('hard_time', True):
                return {'ok': False, 'error': 'hard_time_requires_user_confirmation'}
            if self.fail_save:
                return {'ok': False, 'error': 'injected_storage_failure'}
            # Lock, recheck availability, insert: competing processes cannot reserve one slot twice.
            self.conn.execute('BEGIN IMMEDIATE')
            try:
                old = self.conn.execute('SELECT payload FROM drafts WHERE id=?', (key,)).fetchone()
                if old:
                    self.conn.rollback()
                    return {'ok': True, 'draft_id': key, 'duplicate': True, **json.loads(old[0])}
                if slot not in self.call('query_slots', {}, request)['available']:
                    self.conn.rollback()
                    return {'ok': False, 'error': 'slot_conflict'}
                self.conn.execute('INSERT INTO drafts VALUES (?,?)', (key, json.dumps(payload)))
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise
            return {'ok': True, 'draft_id': key, 'duplicate': False, **payload}
        return {'ok': False, 'error': 'unknown_tool'}

