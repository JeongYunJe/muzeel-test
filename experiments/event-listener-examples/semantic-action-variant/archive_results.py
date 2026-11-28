"""Export small, credential-free evidence from the preserved November 27 runs.

Requires the existing local run directories. Does not run Muzeel or a browser.
"""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
UPSTREAM = ROOT / 'experiments/async-react-muzeel-original/upstream/browser_interaction_bot'
EVIDENCE = HERE / 'evidence'
HISTORY = HERE / 'history'
CORE = {'HTMLDocumentUtil.py': 'HTMLDocumentUtil.py',
        'event_handling/DefaultEventHandler.py': 'DefaultEventHandler.py',
        'ChromeExecution.py': 'ChromeExecution.py'}


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def patch(before, after):
    lines = []
    for relative in CORE:
        delta = difflib.unified_diff(
            (before / relative).read_text().splitlines(keepends=True),
            (after / relative).read_text().splitlines(keepends=True),
            fromfile='a/browser_interaction_bot/' + relative,
            tofile='b/browser_interaction_bot/' + relative)
        lines.extend(line if line.endswith('\n') else
                     line + '\n\\ No newline at end of file\n' for line in delta)
    return ''.join(lines)


def reduced_check(record):
    checks = []
    for item in record['checks']:
        state = item.get('state', {})
        errors = state.get('errors', [])
        checks.append({'name': item['name'], 'passed': item['passed'],
                       'state': {k: state[k] for k in ['input', 'pending', 'lessons',
                                 'checked', 'selected', 'activeText', 'transition']
                                 if k in state and k != 'activeText'},
                       'error_messages': sorted({e.get('message') or e.get('rejection')
                                                 for e in errors})})
    return {k: record[k] for k in ['label', 'browser', 'passed', 'total',
                                   'asset_sha256'] if k in record} | {'checks': checks}


def main():
    EVIDENCE.mkdir(exist_ok=True)
    HISTORY.mkdir(exist_ok=True)
    stages = [
        ('react-original', ROOT / 'experiments/event-listener-examples/semantic-action-variant/experiments/react/original/runs/terminal-20261127-171224-b583c8'),
        ('react-semantic-before-xpath', HERE / 'experiments/react/semantic-dedup/runs/terminal-20261127-170921-e9be49'),
        ('react-semantic-xpath', HERE / 'experiments/react/semantic-dedup/runs/terminal-20261127-171716-9eb636'),
        ('react-search-az', HERE / 'experiments/react/semantic-dedup/runs/terminal-20261127-195657-7229ab'),
        ('react-search-az-af', HERE / 'experiments/react/semantic-dedup/runs/terminal-20261127-203248-83e359'),
        ('vue-original', ROOT / 'experiments/async-vue-muzeel-original/runs/terminal-20261112-122442-7cd670'),
        ('vue-search-az-af', HERE / 'experiments/vue/semantic-dedup/runs/terminal-20261127-214229-584073')]
    measured = []
    for name, run in stages:
        summary = read(run / 'summary.json')
        entry = {'stage': name, 'run_path': str(run.relative_to(ROOT)),
                 'seconds': float(summary['completed_sites_record'].rsplit(',', 1)[1]),
                 **{k: summary[k] for k in [
                     'browser_version', 'preset', 'total_instrumented_ordinary_functions',
                     'observed_function_ids_in_external_log_capture',
                     'unobserved_function_ids_in_external_log_capture',
                     'actual_removed_body_ranges', 'original_bytes', 'original_sha256',
                     'optimized_bytes', 'optimized_sha256', 'initial_event_candidates',
                     'trace_last_event_types', 'captured_log_predicts_same_removal_ranges']}}
        work = run / 'muzeel/browser_interaction_bot'
        entry['core_sources_sha256'] = {relative: digest(work / relative) for relative in CORE}
        measured.append(entry)
    write(EVIDENCE / 'optimization-history.json', {
        'measurement': 'completed_sites_record, one run per condition; excludes launcher preparation and server startup',
        'react_experiment_date': '2026-11-27', 'vue_original_date': '2026-11-12',
        'vue_modified_date': '2026-11-27', 'runs': measured})

    snapshots = [(UPSTREAM, 'upstream')]
    for name, run in stages[1:5]:
        snapshots.append((run / 'muzeel/browser_interaction_bot', name))
    for index, ((before, _), (after, name)) in enumerate(zip(snapshots, snapshots[1:]), 1):
        (HISTORY / f'{index:02}-{name}.patch').write_text(patch(before, after))
    latest = snapshots[-1][0]
    assert all((latest / relative).read_bytes() == (HERE / local).read_bytes()
               for relative, local in CORE.items())
    (HERE / 'semantic-actions.patch').write_text(patch(UPSTREAM, latest))
    write(HERE / 'source-sha256.json', {relative: {
        'upstream_sha256': digest(UPSTREAM / relative),
        'variant_sha256': digest(HERE / local)} for relative, local in CORE.items()})

    suite = HERE / 'suite-20261127-170242'
    initial = read(suite / 'validation/results.json')
    write(EVIDENCE / 'initial-validation.json', {
        'scope': 'Initial semantic/XPath variant; predates a-z and a-f changes',
        'controls_checks': read(HERE / 'browser-checks.json'),
        'results': [{k: item[k] for k in ['label', 'target', 'policy', 'variant',
                                         'passed', 'total', 'browser'] if k in item}
                    for item in initial]})
    fixture_rows = read(suite / 'results.json')
    write(EVIDENCE / 'fixture-results.json', [{
        'target': r['target'], 'policy': r['policy'],
        'seconds': float(r['summary']['completed_sites_record'].rsplit(',', 1)[1]),
        **{k: r['summary'][k] for k in ['initial_event_candidates',
            'total_instrumented_ordinary_functions', 'observed_function_ids_in_external_log_capture',
            'actual_removed_body_ranges', 'original_bytes', 'optimized_bytes']}}
        for r in fixture_rows if r['target'] != 'react'])
    checks = ROOT / 'diagnostics/async-react-latest-validation-20261127'
    write(EVIDENCE / 'latest-react-validation.json', {
        'browser_scope': 'Chrome 158 desktop; exact latest React optimized asset',
        'initial_suite': [reduced_check(r) for r in read(checks / 'results.json')],
        'settled_click_followup': [reduced_check(r) for r in read(checks / 'settled-results.json')],
        'rapid_search_repeats': [reduced_check(r) for r in read(checks / 'rapid-repeat-results.json')
                                 if r['label'].startswith('optimized-rapid-repeat')],
        'confirmed_regressions': read(checks / 'findings.json')['confirmed_regressions'],
        'excluded_initial_failures': read(checks / 'findings.json')['excluded_initial_failures'],
        'vue_functional_validation': 'not performed for the latest Vue output at user request'})
    analysis = ROOT / 'diagnostics/async-react-deleted-functions-20261127'
    deleted = read(analysis / 'summary.json')
    write(EVIDENCE / 'deleted-functions-summary.json', {
        **{k: deleted[k] for k in ['original_sha256', 'source_map_matches_frozen_input',
            'total_ordinary_functions', 'observed', 'unobserved', 'removed_body_ranges',
            'nested_ordinary_functions_removed_with_parent', 'removed_bytes', 'groups']},
        'cleanup_restoration': {'diagnostic_only': True, 'body_start': 226540,
            'role': 'clear pending commit callback and timers on cancellation',
            'body': 'state.unsuspend = null; clearTimeout(stylesheetTimer); clearTimeout(imgTimer);',
            'result': [reduced_check(r) for r in read(analysis / 'cleanup-restoration-results.json')],
            'not_applied_to_exploration_code_or_latest_optimized_output': True}})
    candidates = read(analysis / 'conditional-removal-candidates.json')
    write(EVIDENCE / 'conditional-removal-candidates.json', {
        **{k: candidates[k] for k in ['scope', 'judgment', 'count', 'bytes']},
        'groups': [{'category': g['category'], 'body_starts': g['starts'],
                    'count': g['count'], 'bytes': g['bytes'], 'condition': g['condition']}
                   for g in candidates['groups']],
        'not_an_implemented_removal_policy': True})
    print('Exported historical patches and compact evidence; no experiments were rerun.')


if __name__ == '__main__':
    main()
