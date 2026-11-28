"""User-owned terminal run of original Muzeel against the frozen Vue build."""
import argparse
import ast
from collections import Counter
from contextlib import closing, redirect_stdout
from datetime import datetime
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import re
import runpy
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parent
SHARED = BASE.parent / 'async-react-muzeel-original'
APP = BASE.parents[1] / 'async-vue'
PINNED = SHARED / 'browser/150.0.7871.124'
SOURCE_CONFIG = Path('/Users/jeong-yunje/Documents/muzeel-reproduction/Muzeel/config.py')
PYTHON = sys.executable
MITMDUMP = Path(PYTHON).parent / 'mitmdump'
LIST = 'async_vue_original'
RUN = None
CHILDREN = []
HANDLES = []
ENV = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUNBUFFERED': '1'}
# Experiment launcher only: exact approved source replacements in new copies.
CODE_PATCHES = {}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def config(path=SOURCE_CONFIG):
    tree = ast.parse(path.read_text())
    return next(ast.literal_eval(node.value) for node in tree.body
                if isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == 'db_details' for target in node.targets))


def database(settings=None):
    import pymysql
    settings = settings or config()
    return pymysql.connect(host='127.0.0.1', user=settings.get('user') or settings['username'],
                           password=settings['password'], port=settings['port'],
                           database='muzeel', connect_timeout=5)


def status(value, **details):
    if RUN:
        write_json(RUN / 'launcher-status.json', {'status': value, **details})


def stop(process):
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=5)
    except ProcessLookupError:
        pass
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def foreground(command, label):
    command = [str(x) for x in command]
    print('\n[' + label + ']\n$ ' + shlex.join(command), flush=True)
    process = subprocess.Popen(command, cwd=BASE, env=ENV, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, errors='replace',
                               bufsize=1, start_new_session=True)
    CHILDREN.append(process)
    with (RUN / (label + '.log')).open('w') as output:
        for line in process.stdout:
            print(line, end='', flush=True)
            output.write(line)
            output.flush()
    if process.wait() != 0:
        raise RuntimeError(label + ' 단계가 실패했습니다. 로그를 확인하세요.')


def background(command, label, cwd):
    handle = (RUN / (label + '.log')).open('w')
    HANDLES.append(handle)
    process = subprocess.Popen([str(x) for x in command], cwd=cwd, env=ENV,
                               stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
    CHILDREN.append(process)
    print('[백그라운드] ' + label + ': ' + str(RUN / (label + '.log')), flush=True)
    return process


def wait_port(port, process):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('서버가 종료됐습니다. 해당 로그를 확인하세요.')
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.3):
                return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError('서버 시작 시간 초과: ' + str(port))


def available_ports(site_port):
    if site_port in (9700, 9701) or not 1024 <= site_port <= 65535:
        raise RuntimeError('사이트 포트는 9700·9701을 제외한 1024~65535여야 합니다.')
    for port in [site_port, 9700, 9701]:
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', port)) == 0:
                raise RuntimeError(str(port) + ' 포트가 사용 중입니다. 다른 프로세스를 자동 종료하지 않습니다.')


def preflight():
    import esprima
    import chromedriver_autoinstaller
    upstream = json.loads((SHARED / 'UPSTREAM.json').read_text())
    for name, expected in upstream['sha256'].items():
        if digest(SHARED / 'upstream' / name) != expected:
            raise RuntimeError('원본 Muzeel 해시 불일치: ' + name)
    build = json.loads((BASE / 'input-manifest.json').read_text())
    for name, expected in build['sha256'].items():
        if digest(BASE / 'site-es2017' / name) != expected:
            raise RuntimeError('고정 입력 빌드가 변경됐습니다: ' + name)
    versions = {}
    for name, expected in [('esprima', '4.0.1'), ('selenium', '4.8.3'), ('selenium-wire', '5.1.0'),
                           ('mitmproxy', '9.0.1'), ('PyMySQL', '0.10.1'), ('chromedriver-autoinstaller', '0.6.4')]:
        versions[name] = importlib.metadata.version(name)
        if versions[name] != expected:
            raise RuntimeError(name + ' 버전이 다릅니다. 기존 muzeel-reproduction 가상환경을 활성화하세요.')
    driver = PINNED / 'chromedriver-mac-arm64/chromedriver'
    chrome = PINNED / 'chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'
    for path in [driver, chrome, MITMDUMP, APP / 'node_modules/vite/bin/vite.js']:
        if not path.is_file():
            raise RuntimeError('필요 파일이 없습니다: ' + str(path))
    if not (driver.parent / 'Google Chrome for Testing.app').is_dir() or shutil.which('node') is None:
        raise RuntimeError('고정 브라우저 링크 또는 node 실행 경로를 확인하세요.')
    system_version = chromedriver_autoinstaller.get_chrome_version()
    cache = Path(chromedriver_autoinstaller.__file__).parent / system_version.split('.')[0]
    if not (cache / 'chromedriver').is_file():
        raise RuntimeError('시스템 Chrome용 캐시가 없습니다. python terminal_run.py --prepare-driver-cache 를 먼저 실행하세요.')
    ENV['PATH'] = os.pathsep.join([str(driver.parent), str(cache), os.environ['PATH']])
    source = BASE / 'site-es2017' / build['javascript']['path']
    counts = {'ordinary_functions': 0, 'arrow_functions': 0}
    def delegate(node, metadata):
        if node.type in ('FunctionDeclaration', 'FunctionExpression'):
            counts['ordinary_functions'] += 1
        elif node.type == 'ArrowFunctionExpression':
            counts['arrow_functions'] += 1
    parsed = esprima.parseModule(source.read_text(), {'range': True, 'tolerant': True}, delegate)
    subprocess.run(['node', '--check', str(source)], check=True, stdout=subprocess.DEVNULL)
    report = {'upstream_commit': upstream['commit'], 'upstream_files_checked': len(upstream['sha256']),
              'input_js': build['javascript'], **counts, 'tolerated_diagnostics': list(parsed.errors),
              'python': PYTHON, 'dependencies': versions, 'system_chrome': system_version,
              'system_driver_cache': str(cache), 'pinned_browser': '150.0.7871.124',
              'optimization_executed_by_check': False}
    print('[준비 확인] 원본 Muzeel ' + str(len(upstream['sha256'])) + '개 파일·입력 빌드 해시 일치', flush=True)
    print('[입력] ' + str(source) + '\n       ' + str(source.stat().st_size) + ' bytes / ' + digest(source), flush=True)
    print('[파서] 일반 함수 ' + str(counts['ordinary_functions']) + ', 화살표 함수 ' + str(counts['arrow_functions']) + ', tolerated 진단 ' + str(len(parsed.errors)), flush=True)
    print('[브라우저] 실험 Chrome 150 / 시스템 Chrome ' + system_version + ' 캐시 확인', flush=True)
    return build, report


def network_check(host):
    if socket.gethostbyname(host) != '127.0.0.1':
        raise RuntimeError('별칭이 로컬 127.0.0.1로 해석되지 않습니다.')
    with closing(database()) as db:
        with db.cursor() as cursor:
            cursor.execute('SELECT 1')
            if cursor.fetchone()[0] != 1:
                raise RuntimeError('DB 읽기 검사에 실패했습니다.')
            cursor.execute('SELECT requestUrl,contFilePath,updateFilePath FROM cachedPages LIMIT 0')
    print('[연결 확인] 별칭 DNS·기존 Muzeel DB 읽기 정상', flush=True)


def browser_check():
    code = """import os,shutil,json
import chromedriver_autoinstaller
before=shutil.which('chromedriver')
chromedriver_autoinstaller.install()
assert shutil.which('chromedriver')==before, 'Autoinstaller changed pinned driver selection'
from seleniumwire import webdriver
from selenium.webdriver import ChromeOptions
options=ChromeOptions()
options.add_argument('--headless')
options.add_experimental_option('mobileEmulation',{'deviceName':'iPhone X'})
driver=webdriver.Chrome(options=options)
try:
 assert driver.capabilities['browserVersion']=='150.0.7871.124'
 assert driver.execute_script('return screen.width')==375
 print(json.dumps({'browser':driver.capabilities['browserVersion'],'device':'iPhone X','url':driver.current_url}))
finally: driver.quit()
"""
    subprocess.run([PYTHON, '-c', code], env=ENV, check=True)
    print('[빈 창 검사] Chrome 150 / iPhone X 정상. 대상 사이트·탐색·제거는 실행하지 않았습니다.', flush=True)


def prepare(site_port, environment):
    global RUN
    stamp = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y%m%d-%H%M%S')
    name = 'terminal-' + stamp + '-' + uuid.uuid4().hex[:6]
    host = 'vue-muzeel-' + name.removeprefix('terminal-') + '.127.0.0.1.nip.io'
    site = 'http://' + host + ':' + str(site_port) + '/'
    network_check(host)
    with closing(database()) as db:
        with db.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM cachedPages WHERE initiatingUrl IN (%s,%s)', (site, site + '/'))
            if cursor.fetchone()[0]:
                raise RuntimeError('새 URL의 캐시가 이미 있습니다. 새 실행으로 다시 시도하세요.')
            cursor.execute('SELECT * FROM cachedPages ORDER BY id')
            snapshot = {str(row[0]): hashlib.sha256(json.dumps(row, default=str).encode()).hexdigest() for row in cursor.fetchall()}
    RUN = BASE / 'runs' / name
    RUN.mkdir(parents=True)
    work = RUN / 'muzeel'
    manifest = json.loads((SHARED / 'UPSTREAM.json').read_text())
    for relative in manifest['sha256']:
        target = work / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SHARED / 'upstream' / relative, target)
    for relative, content in CODE_PATCHES.items():
        (work / relative).write_text(content)
    source = config()
    local = {'host': '127.0.0.1', 'database': 'muzeel', 'username': source['username'],
             'user': source.get('user') or source['username'], 'password': source['password'],
             'port': source['port'], 'cache_directory': str(work)}
    target = work / 'config.py'
    target.chmod(0o600)
    target.write_text('db_details = ' + repr(local) + '\n')
    for folder in ['data/muzeel', 'errors_internal', 'results_internal', 'outputs_internal', 'sites_lists']:
        (work / folder).mkdir(parents=True, exist_ok=True)
    (work / 'sites_lists' / LIST).write_text(site)
    write_json(RUN / 'existing-row-sha256-before.json', snapshot)
    write_json(RUN / 'preflight.json', environment)
    write_json(RUN / 'run-settings.json', {'site': site, 'host': host, 'site_port': site_port,
               'database': 'muzeel', 'upstream_commit': manifest['commit'],
               'configuration_only_changes': ['config.py'], 'algorithm_files_changed': sorted(CODE_PATCHES),
               'algorithm_variant': 'button-candidates',
               'patch_sha256': {name: hashlib.sha256(content.encode()).hexdigest() for name, content in CODE_PATCHES.items()},
               'preset': 'iPhone X', 'browser': '150.0.7871.124', 'frozen_input': str(BASE / 'site-es2017')})
    status('PREPARED')
    return site, host


def cache_check(site, build):
    work = RUN / 'muzeel'
    with closing(database(config(work / 'config.py'))) as db:
        with db.cursor() as cursor:
            cursor.execute('SELECT requestUrl,contFilePath,updateFilePath,type FROM cachedPages WHERE initiatingUrl=%s', (site,))
            rows = cursor.fetchall()
    entries = []
    for url, file, updated, kind in rows:
        if updated:
            path = work / 'data' / file
            entries.append({'url': url, 'cache_file': file, 'bytes': path.stat().st_size,
                            'sha256': digest(path), 'content_type': kind})
    if len(entries) != 1 or entries[0]['sha256'] != build['javascript']['sha256']:
        raise RuntimeError('JS 캐시가 고정 입력과 일치하지 않아 탐색·제거를 시작하지 않습니다.')
    if (work / 'error_log_clone').read_text().strip():
        raise RuntimeError('수집 오류가 기록됐습니다. 탐색·제거를 시작하지 않습니다.')
    write_json(RUN / 'cache-validation.json', {'site': site, 'cached_resources': len(rows), 'javascript': entries})
    print('[캐시 확인] 대상 JS 1개 / 고정 입력과 해시 일치', flush=True)


def analyze(site, build):
    sys.path.insert(0, str(SHARED / 'upstream'))
    from DataStore import DataStore
    from LogParser import LogParser
    from EliminationUtils import EliminationUtils
    work = RUN / 'muzeel'
    item = json.loads((RUN / 'cache-validation.json').read_text())['javascript'][0]
    url, file = item['url'], item['cache_file']
    original = work / 'data' / file
    optimized = work / 'data/muzeel' / (original.stem + '.m')
    store = DataStore.__new__(DataStore)
    store.data_map = {url: {'original': original.read_text(), 'updated': original.read_text()}}
    store.function_id_map = {}
    with redirect_stdout(io.StringIO()):
        store._DataStore__populate_function_id_map()
    log = RUN / 'captured-browser.log'
    observed = LogParser.parse_logs(set(log.read_text(errors='replace').splitlines()) if log.exists() else set(), {url: file})
    unused = EliminationUtils.determine_unused_functions(store.function_id_map, observed)
    expected = EliminationUtils.remove_nested_functions_from_start_end_list(EliminationUtils.convert_function_ids_to_start_end_list(unused[url]))
    ranges = work / 'ranges' / site.replace('/', '_') / (original.stem + '.txt')
    actual = [[int(v) for v in line.split(',')] for line in ranges.read_text().splitlines() if line] if ranges.exists() else []
    text = (RUN / 'optimize.log').read_text(errors='replace')
    errors = (work / 'errors_internal' / ('error_log_' + LIST)).read_text()
    completed = (work / 'results_internal' / ('completed_sites_' + LIST)).read_text()
    trace = work / 'outputs_internal' / site.replace('/', '_') / 'trace'
    records = [json.loads(line) for line in trace.read_text().splitlines() if line] if trace.exists() else []
    manifest = json.loads((SHARED / 'UPSTREAM.json').read_text())
    changed = [name for name, value in manifest['sha256'].items() if digest(work / name) != value]
    report = {'site': site, 'upstream_commit': manifest['commit'], 'browser_version': '150.0.7871.124', 'preset': 'iPhone X',
              'changed_upstream_files_in_execution_copy': changed, 'algorithm_variant': 'button-candidates', 'runtime_complete_marker': '\nComplete\n' in text,
              'error_log': errors, 'completed_sites_record': completed,
              'initial_event_candidates': [int(x) for x in re.findall(r'No of events:\s*(\d+)', text)],
              'trace_records': len(records), 'trace_last_event_types': dict(Counter(row[-1]['event'] for row in records if row)),
              'total_instrumented_ordinary_functions': len(store.function_id_map[url]),
              'observed_function_ids_in_external_log_capture': len(observed[url] & store.function_id_map[url]),
              'unobserved_function_ids_in_external_log_capture': len(unused[url]),
              'actual_removed_body_ranges': len(actual), 'captured_log_predicts_same_removal_ranges': sorted(actual) == sorted(expected),
              'original_bytes': original.stat().st_size, 'original_sha256': digest(original),
              'optimized_bytes': optimized.stat().st_size if optimized.exists() else None,
              'optimized_sha256': digest(optimized) if optimized.exists() else None,
              'range_file': str(ranges), 'independent_validation_completed': False, 'functional_safety_verified': False,
              'result_status': 'completed_validation_pending'}
    if report['optimized_bytes'] is not None:
        report['byte_reduction_percent'] = 100 * (1 - report['optimized_bytes'] / report['original_bytes'])
    with closing(database()) as db:
        with db.cursor() as cursor:
            cursor.execute('SELECT * FROM cachedPages ORDER BY id')
            current = {str(row[0]): hashlib.sha256(json.dumps(row, default=str).encode()).hexdigest() for row in cursor.fetchall()}
    before = json.loads((RUN / 'existing-row-sha256-before.json').read_text())
    report['preexisting_database_rows_unchanged'] = all(current.get(key) == value for key, value in before.items())
    write_json(RUN / 'summary.json', report)
    if not report['runtime_complete_marker'] or errors.strip() or not completed.strip() or not optimized.exists():
        raise RuntimeError('원본 실행이 정상 완료되지 않았습니다. summary.json과 원본 로그를 보존했습니다.')
    if sorted(changed) != sorted(['config.py', *CODE_PATCHES]):
        raise RuntimeError('실행 사본에서 승인한 패치 외의 코드 변경을 발견했습니다.')
    target = RUN / 'site-es2017-optimized'
    shutil.copytree(BASE / 'site-es2017', target)
    shutil.copy2(optimized, target / build['javascript']['path'])
    print('\n[집계] 관측 ' + str(report['observed_function_ids_in_external_log_capture']) + ' / ' + str(report['total_instrumented_ordinary_functions']) + ', 제거 범위 ' + str(len(actual)), flush=True)
    print('[크기] ' + str(report['original_bytes']) + ' → ' + str(report['optimized_bytes']) + ' bytes (' + format(report['byte_reduction_percent'], '.2f') + '% 감소)', flush=True)
    if not report['captured_log_predicts_same_removal_ranges']:
        print('[로그 주의] 외부 로그로 예측한 제거 범위와 실제 범위가 다릅니다. 관측 수를 확정값으로 사용하지 마세요.', flush=True)


def internal(stage, run):
    work = run / 'muzeel'
    site = (work / 'sites_lists' / LIST).read_text()
    if stage == 'capture':
        source = work / 'outputs_internal' / site.replace('/', '_') / 'chrome_data/Default/chrome_debug.log'
        deadline = time.monotonic() + 7500
        while not source.exists():
            if time.monotonic() > deadline:
                raise RuntimeError('Chrome 함수 로그가 생성되지 않았습니다.')
            time.sleep(0.1)
        with source.open('rb') as reader, (run / 'captured-browser.log').open('wb') as writer:
            while True:
                chunk = reader.read(1024 * 1024)
                if chunk:
                    writer.write(chunk); writer.flush(); continue
                if not source.exists() or time.monotonic() > deadline:
                    break
                time.sleep(0.1)
        return
    if stage == 'cache':
        os.environ['CHROME_LOG_FILE'] = str(run / 'cache-browser.log')
        sys.argv = ['scraper.py', '9701', 'sites_lists/' + LIST]
        entry = work / 'scraper.py'
    else:
        log = work / 'outputs_internal' / site.replace('/', '_') / 'chrome_data/Default/chrome_debug.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        os.environ['CHROME_LOG_FILE'] = str(log)
        sys.argv = ['run_test.py', LIST, '9700']
        entry = work / 'run_test.py'
    os.chdir(work)
    sys.path.insert(0, str(work))
    runpy.run_path(str(entry), run_name='__main__')


def main():
    global RUN
    parser = argparse.ArgumentParser(description='사용자 터미널에서 원본 Muzeel로 Vue 빌드를 수집·탐색·제거합니다.')
    parser.add_argument('--check', action='store_true', help='파일·의존성·파싱 검사만 실행')
    parser.add_argument('--network-check', action='store_true', help='--check에서 DNS·DB 읽기 검사 추가')
    parser.add_argument('--browser-check', action='store_true', help='--check에서 빈 Chrome 창 생성 검사 추가')
    parser.add_argument('--prepare-driver-cache', action='store_true', help='시스템 Chrome용 드라이버 캐시만 준비')
    parser.add_argument('--prepare-only', action='store_true', help='새 실행 폴더만 준비하고 수집·탐색·제거는 하지 않음')
    parser.add_argument('--run', help='--prepare-only로 생성한 실행 이름')
    parser.add_argument('--site-port', type=int, help='사이트 포트 (기본 4194)')
    parser.add_argument('--_stage', choices=['cache', 'optimize', 'capture'], help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.run and not re.fullmatch(r'[A-Za-z0-9_-]+', args.run):
        raise RuntimeError('올바른 실행 폴더 이름을 지정하세요.')
    if args._stage:
        internal(args._stage, BASE / 'runs' / args.run)
        return
    if args.prepare_driver_cache:
        import chromedriver_autoinstaller
        path = chromedriver_autoinstaller.install()
        if not path:
            raise RuntimeError('드라이버 캐시를 준비하지 못했습니다.')
        print('시스템용 드라이버 캐시: ' + path + '\nMuzeel 최적화는 실행하지 않았습니다.')
        return
    build, environment = preflight()
    if args.check:
        if args.network_check:
            network_check('vue-muzeel-check.127.0.0.1.nip.io')
            available_ports(args.site_port or 4194)
        if args.browser_check:
            browser_check()
        write_json(BASE / 'readiness.json', {**environment,
                   'checked_at': datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
                   'network_read_check_passed': bool(args.network_check),
                   'blank_browser_check_passed': bool(args.browser_check),
                   'site_port_checked': (args.site_port or 4194) if args.network_check else None,
                   'run_created': False})
        print('실행 전 검사 완료. 대상 사이트 수집·탐색·제거는 실행하지 않았습니다.', flush=True)
        return
    if args.network_check or args.browser_check:
        parser.error('--network-check와 --browser-check는 --check와 함께 사용하세요.')
    if args.run:
        candidate = BASE / 'runs' / args.run
        if json.loads((candidate / 'launcher-status.json').read_text())['status'] != 'PREPARED':
            raise RuntimeError('PREPARED 상태의 실행만 시작할 수 있습니다. 부분 결과는 새 실행과 분리하세요.')
        settings = json.loads((candidate / 'run-settings.json').read_text())
        site, host, site_port = settings['site'], settings['host'], settings['site_port']
        if args.site_port and args.site_port != site_port:
            raise RuntimeError('준비된 실행의 포트와 다릅니다.')
        network_check(host)
        RUN = candidate
    else:
        site_port = args.site_port or 4194
        available_ports(site_port)
        site, host = prepare(site_port, environment)
    print('\n실행 폴더: ' + str(RUN) + '\n대상 URL: ' + site, flush=True)
    if args.prepare_only:
        print('\n준비만 완료했습니다. 수집·탐색·제거는 실행하지 않았습니다.\n시작: python terminal_run.py --run ' + RUN.name, flush=True)
        return
    available_ports(site_port)
    work = RUN / 'muzeel'
    manifest = json.loads((SHARED / 'UPSTREAM.json').read_text())
    for name, expected in manifest['sha256'].items():
        if name in CODE_PATCHES:
            expected = hashlib.sha256(CODE_PATCHES[name].encode()).hexdigest()
        if name != 'config.py' and digest(work / name) != expected:
            raise RuntimeError('실행 사본이 원본 또는 지정한 패치와 다릅니다: ' + name)
    if config(work / 'config.py').get('cache_directory') != str(work):
        raise RuntimeError('실행 사본의 캐시 경로가 이 실행 폴더와 다릅니다.')
    status('STARTING')
    ENV['__VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS'] = host
    server = background(['node', APP / 'node_modules/vite/bin/vite.js', 'preview', '--outDir', BASE / 'site-es2017',
                         '--host', '127.0.0.1', '--port', str(site_port), '--strictPort'], 'site-server', APP)
    wait_port(site_port, server)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(site + build['javascript']['path'], timeout=10) as response:
        if hashlib.sha256(response.read()).hexdigest() != build['javascript']['sha256']:
            raise RuntimeError('서버에서 받은 JS가 고정 입력과 다릅니다.')
    proxy_args = ['--listen-host', '127.0.0.1', '--set', 'confdir=' + str(RUN / 'proxy-conf')]
    cache = background([MITMDUMP, '-s', 'cache_proxy.py', '--listen-port', '9701', *proxy_args], 'cache-proxy', work / 'proxies')
    wait_port(9701, cache)
    status('COLLECTING')
    foreground([PYTHON, '-u', __file__, '--_stage', 'cache', '--run', RUN.name], 'cache')
    cache_check(site, build)
    stop(cache)
    replay = background([MITMDUMP, '-s', 'read_proxy.py', '--listen-port', '9700', *proxy_args], 'read-proxy', work / 'proxies')
    wait_port(9700, replay)
    capture = background([PYTHON, '-u', __file__, '--_stage', 'capture', '--run', RUN.name], 'log-capture', BASE)
    status('EXPLORING')
    foreground([PYTHON, '-u', __file__, '--_stage', 'optimize', '--run', RUN.name], 'optimize')
    try:
        capture.wait(timeout=5)
    except subprocess.TimeoutExpired:
        stop(capture)
    status('ANALYZING')
    analyze(site, build)
    status('COMPLETED_VALIDATION_PENDING')
    print('\n원본 Muzeel 실행 완료. 기능 보존은 별도 검증이 필요합니다.\n결과: ' + str(RUN / 'summary.json') + '\n처리 사이트: ' + str(RUN / 'site-es2017-optimized'), flush=True)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        status('INTERRUPTED')
        print('\n사용자가 중단했습니다. 완료 결과로 집계하지 않습니다.', file=sys.stderr)
        sys.exit(130)
    except Exception as error:
        status('FAILED', error_type=type(error).__name__, error=str(error))
        print('\n실행 중단: ' + str(error), file=sys.stderr)
        if RUN:
            (RUN / 'launcher-error.txt').write_text(type(error).__name__ + ': ' + str(error) + '\n')
        sys.exit(1)
    finally:
        for process in reversed(CHILDREN):
            stop(process)
        for handle in HANDLES:
            handle.close()
