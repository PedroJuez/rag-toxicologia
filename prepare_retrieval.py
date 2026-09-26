"""Download optional models explicitly, then warm the local semantic index."""
import os


def main():
    from retrieval import MODEL_DIR, SEMANTIC_MODEL, LAYA_MODEL
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('HF_HOME', str(MODEL_DIR / 'hub'))
    os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
    from huggingface_hub import snapshot_download
    print('Preparando búsqueda semántica…', flush=True)
    snapshot_download(SEMANTIC_MODEL, local_dir=MODEL_DIR / 'semantic',
                      ignore_patterns=['onnx/*', 'openvino/*', 'pytorch_model.bin'])
    print('Preparando LAYA multilingüe…', flush=True)
    snapshot_download(LAYA_MODEL, local_dir=MODEL_DIR / 'laya',
                      ignore_patterns=['*.onnx', '*.bin'])
    from engine import Engine
    from retrieval import semantic_search, laya_rank
    engine = Engine()
    if engine.rows:
        semantic_search('Conservación de muestras', engine.rows)
        print(laya_rank('¿De qué trata el fragmento?', engine.rows[:1]), flush=True)
    print('Modelos preparados. Reinicia la aplicación para utilizarlos.', flush=True)


if __name__ == '__main__':
    main()
