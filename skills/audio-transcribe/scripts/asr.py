#!/usr/bin/env python3
"""Configurable, local ASR worker. No remote connection or task-specific vocabulary."""
import argparse
import hashlib
import json
import time
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def timestamp(seconds, srt=False):
    total = max(0, round(seconds * 1000))
    hours, rest = divmod(total, 3600000)
    minutes, rest = divmod(rest, 60000)
    secs, ms = divmod(rest, 1000)
    return f'{hours:02}:{minutes:02}:{secs:02}{"," if srt else "."}{ms:03}'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audio', type=Path, required=True)
    p.add_argument('--out-dir', type=Path, required=True)
    p.add_argument('--model', default='large-v3')
    p.add_argument('--device', choices=['cuda', 'cpu'], default='cuda')
    p.add_argument('--compute-type')
    p.add_argument('--language', default='zh')
    p.add_argument('--model-cache', type=Path)
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    a.compute_type = a.compute_type or ('int8' if a.device == 'cpu' else 'float16')
    if not a.audio.is_file():
        p.error('input file does not exist')
    parameters = dict(language=a.language, task='transcribe', beam_size=5, best_of=5,
                      temperature=[0, .2, .4, .6, .8, 1], vad_filter=True,
                      vad_parameters={'min_silence_duration_ms': 450},
                      condition_on_previous_text=False)
    if a.dry_run:
        print(json.dumps(dict(model=a.model, device=a.device, compute_type=a.compute_type,
                              parameters=parameters, dry_run=True)))
        return
    outputs = [a.out_dir / ('raw' + ext) for ext in ['.json', '.txt', '.srt']]
    if any(o.exists() for o in outputs):
        p.error('raw output exists; select a new output directory')
    if any(o.resolve() == a.audio.resolve() for o in outputs):
        p.error('output would overwrite the source')
    from faster_whisper import WhisperModel
    initial = sha(a.audio)
    started = time.perf_counter()
    m = WhisperModel(a.model, device=a.device, compute_type=a.compute_type,
                     download_root=str(a.model_cache) if a.model_cache else None)
    loaded = time.perf_counter()
    iterator, info = m.transcribe(str(a.audio), **parameters)
    segments = [{'start': float(s.start), 'end': float(s.end), 'text': s.text.strip()}
                for s in iterator]
    inferred = time.perf_counter()
    if sha(a.audio) != initial:
        raise RuntimeError('source changed during processing')
    metadata = dict(engine='faster-whisper', model=a.model, device=a.device,
                    compute_type=a.compute_type, source_sha256=initial,
                    duration_seconds=info.duration, load_seconds=loaded-started,
                    inference_seconds=inferred-loaded, worker_seconds=inferred-started,
                    parameters=parameters, empty_text_is_not_proof_of_silence=True)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    outputs[0].write_text(json.dumps(dict(metadata=metadata, segments=segments), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    outputs[1].write_text('\n'.join(f'[{timestamp(s["start"])} --> {timestamp(s["end"])}] {s["text"]}' for s in segments)+'\n', encoding='utf-8')
    outputs[2].write_text('\n\n'.join(f'{i}\n{timestamp(s["start"], True)} --> {timestamp(s["end"], True)}\n{s["text"]}' for i,s in enumerate(segments, 1))+'\n', encoding='utf-8')
    print(json.dumps(dict(segments=len(segments), worker_seconds=metadata['worker_seconds'])))


if __name__ == '__main__':
    main()
