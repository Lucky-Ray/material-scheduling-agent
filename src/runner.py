"""Bounded loop, protocol validation and evidence-based business results."""
TOOLS = {'read_material', 'check_rules', 'query_slots', 'save_draft'}
STATUSES = {'completed', 'needs_confirmation', 'blocked', 'failed'}


def validate_request(request):
    if not isinstance(request, dict):
        raise ValueError('request_must_be_object')
    for key in ('material_id', 'requested_slot', 'request_id'):
        if key in request and request[key] is not None and (not isinstance(request[key], str) or not request[key].strip()):
            raise ValueError('invalid_' + key)
    if 'hard_time' in request and not isinstance(request['hard_time'], bool):
        raise ValueError('hard_time_must_be_boolean')


def validate_action(action):
    if not isinstance(action, dict) or not isinstance(action.get('reason', ''), str):
        raise ValueError('invalid_action')
    if 'finish' in action and not isinstance(action['finish'], bool):
        raise ValueError('finish_must_be_boolean')
    if action.get('finish'):
        if 'tool' in action or action.get('status') not in STATUSES:
            raise ValueError('invalid_finish')
    else:
        if action.get('tool') not in TOOLS or not isinstance(action.get('args', {}), dict):
            raise ValueError('invalid_tool_action')
        if action['tool'] == 'save_draft' and not isinstance(action.get('args', {}).get('slot'), str):
            raise ValueError('invalid_slot')


def build_result(request, trace, status, reason):
    latest = {t['tool']: t['result'] for t in trace}
    successful = next((t['result'] for t in reversed(trace) if t['tool'] == 'save_draft' and t['result'].get('ok')), None)
    save_result = latest.get('save_draft')
    rules = latest.get('check_rules', {})
    material = latest.get('read_material', {})
    review = 'blocked' if rules and not rules.get('ok') else ('passed' if rules.get('ok') else 'not_checked')
    missing = list(dict.fromkeys(material.get('missing', []) + rules.get('missing', [])))
    for key in ('material_id', 'requested_slot'):
        if not request.get(key) and key not in missing:
            missing.append(key)
    slots = latest.get('query_slots', {}).get('available', [])
    return {'status': status, 'reason': reason, 'draft': successful or save_result, 'published': False,
            'material_result': {'material_id': request.get('material_id'), 'review_status': review,
                'risk_reasons': rules.get('risks', []), 'missing_fields': missing,
                'suggested_slot': successful['slot'] if successful else (slots[0] if slots and status == 'needs_confirmation' else None),
                'pending_items': missing + (['confirm_alternative_time'] if status == 'needs_confirmation' else []),
                'save_status': 'saved' if successful else ('failed' if save_result else 'not_attempted')},
            'trace': trace}


def run(request, tools, model, max_steps=10):
    trace = []
    try:
        validate_request(request)
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 1:
            raise ValueError('invalid_step_limit')
    except ValueError as exc:
        return build_result(request if isinstance(request, dict) else {}, trace, 'failed', str(exc))
    for step in range(max_steps):
        try:
            action = model.choose(request, trace)
            validate_action(action)
            if action.get('finish'):
                saved = next((t['result'] for t in reversed(trace) if t['tool'] == 'save_draft' and t['result'].get('ok')), None)
                status = action['status']
                if saved:
                    status = 'needs_confirmation' if saved['confirmation'] == 'pending' else 'completed'
                elif status == 'completed' or any(t['tool'] == 'save_draft' and not t['result'].get('ok') for t in trace):
                    status = 'failed'
                return build_result(request, trace, status, action.get('reason', ''))
            name, args = action['tool'], action.get('args', {})
            if name == 'save_draft' and not all(any(t['tool'] == required for t in trace) for required in ('read_material', 'check_rules', 'query_slots')):
                result = {'ok': False, 'error': 'prerequisites_not_observed'}
            else:
                result = tools.call(name, args, request)
            trace.append({'step': step + 1, 'tool': name, 'args': args, 'reason': action.get('reason', ''), 'result': result})
        except Exception as exc:
            return build_result(request, trace, 'failed', type(exc).__name__)
    return build_result(request, trace, 'incomplete', 'step_limit')
