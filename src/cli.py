"""Command-line interface."""
import argparse
import json
from pathlib import Path
from tools import Tools
from models import Model, MockModel
from runner import run

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--mode', choices=['mock', 'live'], default='mock')
    parser.add_argument('--db', default='drafts.sqlite3')
    parser.add_argument('--output')
    parser.add_argument('--fail-save', action='store_true')
    parser.add_argument('--max-steps', type=int, default=10)
    args = parser.parse_args()
    data = json.loads((ROOT / 'data/catalog.json').read_text(encoding='utf-8'))
    request = json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
    tools = Tools(data, args.db, args.fail_save)
    try:
        result = run(request, tools, MockModel() if args.mode == 'mock' else Model(), args.max_steps)
    finally:
        tools.conn.close()
    result['mode'] = args.mode
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding='utf-8')
    print(output)

