"""Regenerate offline evidence and check document links without external services."""
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
summary = {'verification_date': datetime.now(timezone(timedelta(hours=8))).date().isoformat(),
           'timezone': 'Asia/Shanghai', 'python': platform.python_version(),
           'mode': 'offline_mock', 'live_model_verified': False}
env = dict(os.environ, PYTHONUTF8='1')
for label, cmd, log in [
    ('unit_tests', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], 'test-results.txt'),
    ('scenarios', [sys.executable, 'examples/generate.py'], 'generate-results.txt'),
    ('cli', [sys.executable, 'src/agent.py', '--input', 'examples/conflict.input.json', '--mode', 'mock', '--db', ':memory:'], 'cli-conflict-results.txt')]:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
    output = r.stdout + r.stderr
    (ROOT / 'examples' / log).write_text(output, encoding='utf-8')
    summary[label] = {'exit_code': r.returncode, 'log': 'examples/' + log}
    if label == 'unit_tests':
        summary['unit_test_count'] = int(re.search(r'Ran (\d+) tests', output).group(1))
    if r.returncode:
        print(output)
        raise SystemExit(r.returncode)
    print(label + ': PASS')
report = json.loads((ROOT / 'examples/scenario-results.json').read_text(encoding='utf-8'))
summary['scenario_count'] = len(report)
summary['scenario_assertions_passed'] = all(r['passed'] for r in report)
broken = []
for path in [ROOT / 'README.md', *sorted((ROOT / 'docs').glob('*.md')), ROOT / 'examples/INDEX.md']:
    for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
        if '://' not in link and not (path.parent / link.split('#')[0]).exists():
            broken.append([str(path.relative_to(ROOT)), link])
summary['broken_relative_document_links'] = broken
(ROOT / 'examples/verification-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
if broken:
    print(broken)
    raise SystemExit(1)
print('document links: PASS')
print(f"{summary['unit_test_count']} unit tests; {len(report)} scenarios")
