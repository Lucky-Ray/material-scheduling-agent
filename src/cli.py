"""CLI with structured initialization failures and meaningful exit codes."""
import argparse
import json
from pathlib import Path
from tools import Tools
from models import Model, MockModel
from runner import run, validate_request, build_result

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--catalog', default=str(ROOT / 'data/catalog.json'))
    parser.add_argument('--mode', choices=['mock', 'live'], default='mock')
    parser.add_argument('--db', default='drafts.sqlite3')
    parser.add_argument('--output')
    parser.add_argument('--fail-save', action='store_true')
    parser.add_argument('--max-steps', type=int, default=10)
    args = parser.parse_args()
    tools = None
    request = {}
    try:
        request = json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
        validate_request(request)
        if args.max_steps < 1:
            raise ValueError('invalid_step_limit')
        data = json.loads(Path(args.catalog).read_text(encoding='utf-8-sig'))
        tools = Tools(data, args.db, args.fail_save)
        model = MockModel() if args.mode == 'mock' else Model()
        result = run(request, tools, model, args.max_steps)
    except Exception as exc:
        result = build_result(request if isinstance(request, dict) else {}, [], 'failed', type(exc).__name__)
    finally:
        if tools:
            tools.conn.close()
    result['mode'] = args.mode
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        try:
            Path(args.output).write_text(output, encoding='utf-8')
        except OSError as exc:
            result['status'] = 'failed'
            result['reason'] = 'output_write_' + type(exc).__name__
            output = json.dumps(result, ensure_ascii=False, indent=2)
    print(output)
    if result['status'] in ('failed', 'incomplete'):
        raise SystemExit(1)
