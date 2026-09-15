"""Prepare a new local corpus snapshot. Does not index, upload or perform OCR."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def digest(data):
    return hashlib.sha256(data).hexdigest()


def chunks(text, size):
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind('\n\n', start + size // 2, end)
            if boundary >= 0:
                end = boundary + 2
        yield start, end, text[start:end]
        start = end


def prepare(source, output, corpus_id, anydoc_js=None, node='node', size=2400):
    source, output = Path(source).resolve(), Path(output).resolve()
    if not source.is_dir():
        raise ValueError('Source must be an existing directory')
    if not corpus_id.strip() or size < 100:
        raise ValueError('Non-empty corpus ID and chunk size >= 100 required')
    if output == source or source in output.parents or output in source.parents:
        raise ValueError('Source and output must be separate, non-nested directories')
    output.mkdir(parents=True, exist_ok=False)
    normalized = output / 'normalized'
    normalized.mkdir()
    manifest = {'schema_version': 1, 'corpus_id': corpus_id, 'status': 'preparing',
                'chunker': 'paragraph-char-v1', 'chunk_size': size,
                'converter': {'anydoc_js': str(anydoc_js) if anydoc_js else None,
                              'node': node}, 'documents': []}
    manifest_path = output / 'manifest.json'
    if anydoc_js:
        package = Path(anydoc_js).resolve().parent / 'package.json'
        if package.is_file():
            manifest['converter']['package_version'] = json.loads(package.read_text(encoding='utf-8')).get('version')
        if Path(anydoc_js).is_file():
            manifest['converter']['entrypoint_sha256'] = digest(Path(anydoc_js).read_bytes())
    def save():
        temp = output / 'manifest.tmp'
        temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(manifest_path)
    save()
    office = {'.doc', '.docx', '.odt', '.rtf', '.epub', '.pdf', '.ppt', '.pptx',
              '.odp', '.xls', '.xlsx', '.xlsb', '.ods', '.csv'}
    errors = 0
    with (output / 'chunks.jsonl').open('w', encoding='utf-8') as stream:
        for path in sorted(source.rglob('*')):
            if path.is_dir() and not path.is_symlink():
                continue
            rel = path.relative_to(source).as_posix()
            doc_id = digest((corpus_id + '\0' + rel).encode())
            record = {'document_id': doc_id, 'source_file': rel}
            manifest['documents'].append(record)
            try:
                if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != source):
                    raise ValueError('Symbolic links are not ingested')
                data = path.read_bytes()
                version = digest(data)
                record['document_version'] = version
                suffix = path.suffix.lower()
                if suffix in {'.md', '.txt'}:
                    text = data.decode('utf-8-sig')
                    converter = 'utf8-direct'
                elif suffix in office and anydoc_js:
                    result = subprocess.run([node, str(Path(anydoc_js).resolve()), str(path)],
                                            capture_output=True, timeout=120)
                    if result.returncode == 3:
                        raise ValueError('Needs OCR: no document was uploaded by this preparer')
                    if result.returncode:
                        raise ValueError(f'AnyDoc failed with exit code {result.returncode}')
                    text = result.stdout.decode('utf-8')
                    converter = 'anydoc-local'
                else:
                    raise ValueError('Unsupported format or missing --anydoc-js')
                if digest(path.read_bytes()) != version:
                    raise ValueError('Source changed during conversion; retry in a new snapshot')
                if not text.strip():
                    raise ValueError('Empty extracted text')
                text = text.replace('\r\n', '\n').replace('\r', '\n')
                dest = normalized / (doc_id + '.md')
                dest.write_text(text, encoding='utf-8', newline='')
                metadata = dict(record, normalized_file=dest.relative_to(output).as_posix(),
                                normalized_sha256=digest(text.encode()))
                count = 0
                for start, end, content in chunks(text, size):
                    chunk_id = digest(f'{doc_id}:{version}:{start}:{end}:paragraph-char-v1'.encode())
                    item = dict(metadata, chunk_id=chunk_id, corpus_id=corpus_id,
                                locator={'kind': 'normalized_char_offsets', 'start': start, 'end': end},
                                text=content)
                    stream.write(json.dumps(item, ensure_ascii=False) + '\n')
                    count += 1
                record.update(status='ready', converter=converter, chunks=count,
                              normalized_file=metadata['normalized_file'],
                              normalized_sha256=metadata['normalized_sha256'])
            except (ValueError, OSError, UnicodeError, subprocess.SubprocessError) as exc:
                record.update(status='error', error=str(exc))
                errors += 1
            save()
    manifest['status'] = 'incomplete' if errors or not manifest['documents'] else 'complete'
    save()
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--corpus-id', required=True)
    parser.add_argument('--anydoc-js')
    parser.add_argument('--node', default='node')
    parser.add_argument('--size', type=int, default=2400)
    args = parser.parse_args()
    try:
        result = prepare(args.source, args.output, args.corpus_id, args.anydoc_js, args.node, args.size)
    except (ValueError, OSError) as exc:
        parser.exit(2, str(exc) + '\n')
    print(json.dumps({'status': result['status'], 'documents': len(result['documents'])}))
    raise SystemExit(0 if result['status'] == 'complete' else 2)
