"""Compare retrieval only, with optional human evidence labels; no LLM calls."""
import argparse
import json
import time
from pathlib import Path
from engine import Engine


def evaluate(engine, cases, modes):
    known = set(engine.byid)
    for case in cases:
        missing = set(case.get('expected_chunk_ids', [])) - known
        if missing:
            raise ValueError(f"Etiquetas obsoletas en {case['id']}: {sorted(missing)}")
    results = []
    for case in cases:
        for mode in modes:
            started = time.perf_counter()
            result = engine.search(case['question'], mode)
            ids = [s['chunk_id'] for s in result['sources']]
            expected = set(case.get('expected_chunk_ids', []))
            diag = result['retrieval_diagnostics']
            candidates = set(diag.get('candidate_ids', ids))
            item = {'id': case['id'], 'question': case['question'], 'mode': mode,
                    'seconds': round(time.perf_counter() - started, 3),
                    'diagnostics': diag,
                    'sources': [{'chunk_id': s['chunk_id'], 'file': s['source_file'],
                                 'locator': s['locator'], 'text': s['text'],
                                 'relevance': s.get('relevance')} for s in result['sources']]}
            if expected:
                item['evidence_recall_at_6'] = len(expected & set(ids)) / len(expected)
                item['candidate_recall'] = len(expected & candidates) / len(expected)
                item['reciprocal_rank'] = next((1 / (i + 1) for i, cid in enumerate(ids)
                                                if cid in expected), 0)
            if case.get('unanswerable'):
                item['empty_retrieval'] = not ids
            results.append(item)
            print(case['id'], mode, item['seconds'], 's',
                  'LAYA=' + str(diag.get('laya_used', False)), flush=True)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cases', type=Path, default=Path('evaluation/questions.jsonl'))
    parser.add_argument('--output', type=Path, default=Path('evaluation/results.json'))
    parser.add_argument('--limit', type=int)
    parser.add_argument('--modes', nargs='+', default=['baseline', 'graph', 'hybrid', 'laya'],
                        choices=['baseline', 'graph', 'hybrid', 'laya'])
    args = parser.parse_args()
    cases = [json.loads(line) for line in args.cases.read_text(encoding='utf8').splitlines() if line.strip()]
    if args.limit:
        cases = cases[:args.limit]
    results = evaluate(Engine(), cases, args.modes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'scope': 'retrieval_only; seed labels, not expert validation',
                                      'results': results}, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
