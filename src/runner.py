"""Bounded model/tool orchestration and evidence-based final status."""
def run(request, tools, model, max_steps=10):
    trace = []
    for step in range(max_steps):
        try:
            action = model.choose(request, trace)
            if action.get('finish'):
                # Final status derives from tool evidence; never trust a model's success assertion.
                saved = next((t['result'] for t in reversed(trace) if t['tool'] == 'save_draft'), None)
                status = action.get('status', 'blocked')
                if saved and saved.get('ok'):
                    status = 'needs_confirmation' if saved['confirmation'] == 'pending' else 'completed'
                elif status == 'completed':
                    status = 'failed'
                return {'status': status, 'reason': action.get('reason'), 'draft': saved,
                        'published': False, 'trace': trace}
            name, args = action['tool'], action.get('args', {})
            if name == 'save_draft' and not all(any(t['tool'] == required for t in trace) for required in ('read_material', 'check_rules', 'query_slots')):
                result = {'ok': False, 'error': 'prerequisites_not_observed'}
            else:
                result = tools.call(name, args, request)
            trace.append({'step': step + 1, 'tool': name, 'args': args,
                          'reason': action.get('reason', ''), 'result': result})
        except Exception as exc:
            return {'status': 'failed', 'reason': type(exc).__name__, 'published': False, 'trace': trace}
    return {'status': 'incomplete', 'reason': 'step_limit', 'published': False, 'trace': trace}

