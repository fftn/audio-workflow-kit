#!/usr/bin/env python3
"""Local NVIDIA Sortformer worker with explicit, reproducible long-form settings."""
import argparse
import hashlib
import json
import math
import time
from pathlib import Path

MODEL = 'nvidia/diar_streaming_sortformer_4spk-v2.1'
CONFIG = dict(chunk_len=340, chunk_right_context=40, fifo_len=40,
              spkcache_update_period=300, spkcache_len=188)


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(4*1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audio', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--model', default=MODEL)
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    if not a.audio.is_file():
        p.error('input file does not exist')
    if a.dry_run:
        print(json.dumps(dict(model=a.model, device='cuda', config=CONFIG, dry_run=True)))
        return
    if a.output.exists() or a.output.resolve() == a.audio.resolve():
        p.error('output exists or conflicts with the source')
    import torch
    from nemo.collections.asr.models import SortformerEncLabelModel
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA is required for this worker')
    initial = sha(a.audio)
    started = time.perf_counter()
    if Path(a.model).is_file():
        m = SortformerEncLabelModel.restore_from(str(a.model), map_location='cuda', strict=False)
    else:
        m = SortformerEncLabelModel.from_pretrained(a.model, map_location='cuda')
    m = m.to('cuda').eval()
    for key, value in CONFIG.items():
        setattr(m.sortformer_modules, key, value)
    m.sortformer_modules._check_streaming_parameters()
    loaded = time.perf_counter()
    with torch.inference_mode():
        prediction = m.diarize(audio=[str(a.audio)], batch_size=1)
    inferred = time.perf_counter()
    segments = []
    for item in prediction[0]:
        parts = item if isinstance(item, (list, tuple)) else str(item).split()
        if len(parts) < 3:
            raise ValueError('invalid diarization output')
        start, end, speaker = float(parts[0]), float(parts[1]), str(parts[2])
        if not math.isfinite(start+end) or start < 0 or end <= start:
            raise ValueError('invalid diarization time')
        segments.append(dict(start=start, end=end, speaker=speaker))
    if len({s['speaker'] for s in segments}) > 4:
        raise ValueError('unexpected speaker capacity')
    if sha(a.audio) != initial:
        raise RuntimeError('source changed during processing')
    md = dict(engine='NVIDIA NeMo streaming Sortformer', model=a.model, speaker_capacity=4,
              anonymous_labels_only=True, source_sha256=initial, config=CONFIG,
              load_seconds=loaded-started, inference_seconds=inferred-loaded,
              worker_seconds=inferred-started, gpu=torch.cuda.get_device_name(0),
              torch_version=torch.__version__)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(dict(metadata=md, segments=segments), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(segments=len(segments), worker_seconds=md['worker_seconds'])))


if __name__ == '__main__':
    main()
