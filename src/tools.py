"""Local business tools and transactional, request-idempotent draft storage."""
import hashlib
import json
import sqlite3


def request_key(request):
    identity = ({'request_id': request['request_id']} if request.get('request_id') else
                {'material_id': request.get('material_id'), 'requested_slot': request.get('requested_slot')})
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()


class Tools:
    def __init__(self, data, db, fail_save=False):
        self.data = data
        self.fail_save = fail_save
        self.conn = sqlite3.connect(str(db))
        try:
            self.conn.execute('CREATE TABLE IF NOT EXISTS drafts (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
            self.conn.execute('CREATE TABLE IF NOT EXISTS requests (request_key TEXT PRIMARY KEY, draft_id TEXT NOT NULL UNIQUE)')
            # Add request identity to pre-existing draft stores without deleting their data.
            for did, encoded in self.conn.execute('SELECT id, payload FROM drafts').fetchall():
                self.conn.execute('INSERT OR IGNORE INTO requests VALUES (?,?)', (request_key(json.loads(encoded)), did))
            self.conn.commit()
        except Exception:
            self.conn.close()
            raise

    def existing(self, request):
        row = self.conn.execute('SELECT d.id,d.payload FROM requests r JOIN drafts d ON d.id=r.draft_id WHERE r.request_key=?',
                                (request_key(request),)).fetchone()
        return (row[0], json.loads(row[1])) if row else None

    def call(self, name, args, request):
        mid = request.get('material_id')
        material = self.data['materials'].get(mid)
        if name == 'read_material':
            return {'material': material, 'missing': [] if material else ['material_id or material']}
        if name == 'check_rules':
            if not material:
                return {'ok': False, 'missing': ['material'], 'risks': []}
            missing = [k for k in ('title', 'rights') if not material.get(k)]
            risks = [rule for rule in self.data['rules'] if rule in material.get('tags', [])]
            return {'ok': not missing and not risks, 'missing': missing, 'risks': risks}
        if name == 'query_slots':
            occupied = set(self.data['occupied'])
            drafts = [json.loads(row[0]) for row in self.conn.execute('SELECT payload FROM drafts')]
            occupied.update(d['slot'] for d in drafts)
            old = self.existing(request)
            return {'available': [s for s in self.data['slots'] if s not in occupied],
                    'existing': [old[1]] if old else [],
                    'requested_available': request.get('requested_slot') in self.data['slots'] and request.get('requested_slot') not in occupied}
        if name == 'save_draft':
            return self.save(args, request)
        return {'ok': False, 'error': 'unknown_tool'}

    def save(self, args, request):
        if not request.get('requested_slot'):
            return {'ok': False, 'error': 'missing_requested_slot'}
        # Every retry must pass current rules, including retries of an old saved draft.
        rules = self.call('check_rules', {}, request)
        if not rules['ok']:
            return {'ok': False, 'error': 'unsafe_or_incomplete', **rules}
        self.conn.execute('BEGIN IMMEDIATE')
        try:
            old = self.existing(request)
            if old:
                did, payload = old
                if payload['material_id'] != request['material_id'] or payload['requested_slot'] != request['requested_slot']:
                    self.conn.rollback()
                    return {'ok': False, 'error': 'request_id_conflict'}
                if request.get('hard_time', True) and payload['slot'] != request['requested_slot']:
                    self.conn.rollback()
                    return {'ok': False, 'error': 'hard_time_requires_user_confirmation'}
                self.conn.rollback()
                return {'ok': True, 'draft_id': did, 'duplicate': True, **payload}
            slot = args.get('slot')
            if slot != request['requested_slot'] and request.get('hard_time', True):
                self.conn.rollback()
                return {'ok': False, 'error': 'hard_time_requires_user_confirmation'}
            if self.fail_save:
                self.conn.rollback()
                return {'ok': False, 'error': 'injected_storage_failure'}
            if slot not in self.call('query_slots', {}, request)['available']:
                self.conn.rollback()
                return {'ok': False, 'error': 'slot_conflict'}
            payload = {'material_id': request['material_id'], 'slot': slot, 'requested_slot': request['requested_slot'],
                       'confirmation': 'pending' if slot != request['requested_slot'] else 'not_required'}
            if request.get('request_id'):
                payload['request_id'] = request['request_id']
            did = request_key(request)[:20]
            self.conn.execute('INSERT INTO drafts VALUES (?,?)', (did, json.dumps(payload)))
            self.conn.execute('INSERT INTO requests VALUES (?,?)', (request_key(request), did))
            self.conn.commit()
            return {'ok': True, 'draft_id': did, 'duplicate': False, **payload}
        except Exception:
            self.conn.rollback()
            raise
