#!/usr/bin/env python3
"""Preserve ASR text and assign only time-supported anonymous speaker clusters."""
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path


def valid(row):
    return (isinstance(row.get('start'), (int, float)) and isinstance(row.get('end'), (int, float))
            and math.isfinite(row['start']) and math.isfinite(row['end'])
            and 0 <= row['start'] < row['end'])


def align(asr, diar):
    result = []
    duration = asr.get('metadata', {}).get('duration_seconds')
    if any(not valid(d) or (duration is not None and d['end'] > duration + 2) for d in diar['segments']):
        raise ValueError('invalid raw diarization time')
    for raw in asr['segments']:
        row = dict(raw)
        unreliable = bool(raw.get('timestamp_unreliable')) or not valid(raw)
        if not unreliable and duration is not None and raw['end'] > duration + 2:
            unreliable = True
        row.update(speaker='unknown', speaker_overlap_seconds={},
                   timestamp_unreliable=unreliable, possible_overlapping_speech=False)
        if not unreliable:
            scores = defaultdict(float)
            for d in diar['segments']:
                delta = max(0, min(raw['end'], d['end']) - max(raw['start'], d['start']))
                if delta:
                    scores[d['speaker']] += delta
            ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
            row['speaker_overlap_seconds'] = dict(ranked)
            if ranked:
                row['speaker'] = ranked[0][0]
                row['speaker_assignment'] = 'accumulated_time_overlap'
                row['possible_overlapping_speech'] = (len(ranked) > 1 and ranked[1][1] >= .32
                                                      and ranked[1][1] / sum(scores.values()) >= .1)
            else:
                row['speaker_assignment'] = 'no_supported_overlap'
        else:
            row['speaker_assignment'] = 'unreliable_timestamp'
        result.append(row)
    return dict(metadata=dict(asr.get('metadata', {}), layer='derived_anonymous_speakers',
                              alignment='accumulated_time_overlap', speaker_capacity=4), segments=result)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--asr', type=Path, required=True)
    p.add_argument('--diar', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists() or a.output.resolve() in {a.asr.resolve(), a.diar.resolve()}:
        p.error('output exists or conflicts with raw input')
    out = align(json.loads(a.asr.read_text(encoding='utf-8')), json.loads(a.diar.read_text(encoding='utf-8')))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(segments=len(out['segments']))))


if __name__ == '__main__':
    main()
