"""Run isolated original / semantic / deduplicated Muzeel comparisons."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SHARED = ROOT / 'experiments/async-react-muzeel-original'
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--target', choices=['direct', 'delegated', 'controls', 'react', 'vue'], default=os.environ.get('SEMANTIC_TARGET', 'controls'))
parser.add_argument('--policy', choices=['original', 'semantic', 'semantic-dedup'], default=os.environ.get('SEMANTIC_POLICY', 'semantic-dedup'))
args, rest = parser.parse_known_args()
base = HERE / 'experiments' / args.target / args.policy
source = (SHARED / 'site-es2017' if args.target == 'react' else
          ROOT / 'experiments/async-vue-muzeel-original/site-es2017' if args.target == 'vue' else
          HERE / 'controls' if args.target == 'controls' else HERE.parent / args.target)
files = {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in source.rglob('*') if p.is_file() and p.name != '.DS_Store'}
javascript = ('assets/index-9QjRwk1A.js' if args.target == 'react' else
              json.loads((ROOT / 'experiments/async-vue-muzeel-original/input-manifest.json').read_text())['javascript']['path']
              if args.target == 'vue' else 'app.js')
manifest = {'target': 'frozen-input', 'source_project': str(source), 'sha256': files,
            'javascript': {'path': javascript, 'sha256': files[javascript], 'bytes': (source / javascript).stat().st_size}}
if not (base / 'site-es2017').exists():
    base.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, base / 'site-es2017', ignore=shutil.ignore_patterns('.DS_Store'))
    (base / 'input-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
elif json.loads((base / 'input-manifest.json').read_text())['sha256'] != files:
    raise RuntimeError('Frozen input differs; existing runs will not be overwritten.')

spec = importlib.util.spec_from_file_location('isolated_launcher', HERE.parent / 'button-candidate-variant/launcher.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
launcher.BASE = base
launcher.SHARED = SHARED
launcher.APP = ROOT / ('async-react' if args.target == 'react' else 'async-vue')
launcher.PINNED = SHARED / 'browser/150.0.7871.124'
launcher.LIST = 'semantic_' + args.target + '_' + args.policy.replace('-', '_')
launcher.__file__ = str(Path(__file__).resolve())
launcher.ENV.update(SEMANTIC_TARGET=args.target, SEMANTIC_POLICY=args.policy)
if args.policy != 'original':
    for target, name in [('browser_interaction_bot/HTMLDocumentUtil.py', 'HTMLDocumentUtil.py'),
                         ('browser_interaction_bot/ChromeExecution.py', 'ChromeExecution.py'),
                         ('browser_interaction_bot/event_handling/DefaultEventHandler.py', 'DefaultEventHandler.py')]:
        content = (HERE / name).read_text()
        if args.policy == 'semantic':
            content = content.replace('DEDUPLICATE_ACTIONS = True', 'DEDUPLICATE_ACTIONS = False')
        launcher.CODE_PATCHES[target] = content
write = launcher.write_json
def tagged_write(path, value):
    if isinstance(value, dict) and 'algorithm_variant' in value:
        value['algorithm_variant'] = args.policy
        if args.policy != 'original':
            value['search_input_policy'] = 'individual lowercase a-z queries plus same-page a-f input/backspace cycle (50ms pauses)'
    write(path, value)
launcher.write_json = tagged_write
sys.argv = [str(Path(__file__).resolve()), *rest]
if '--site-port' not in rest:
    sys.argv += ['--site-port', '5351']
def timeout(signum, frame):
    raise TimeoutError('Experiment exceeded 15 minutes; partial results are preserved.')
signal.signal(signal.SIGALRM, timeout)
signal.alarm(900)
try:
    launcher.main()
except BaseException as exc:
    launcher.status('FAILED', error_type=type(exc).__name__, error=str(exc))
    raise
finally:
    for process in reversed(launcher.CHILDREN):
        launcher.stop(process)
    for handle in launcher.HANDLES:
        handle.close()
