#!/usr/bin/env python3
"""Estimate serial compute and transfer time; inputs are assumptions, not measurements."""
import argparse
import json
import math


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audio-hours', type=float, required=True)
    p.add_argument('--asr-rtf', type=float, required=True)
    p.add_argument('--diar-rtf', type=float, default=0)
    p.add_argument('--secondary-rtf', type=float, default=0)
    p.add_argument('--retry-fraction', type=float, default=0)
    p.add_argument('--sample-rate', type=int, default=16000)
    p.add_argument('--channels', type=int, default=1)
    p.add_argument('--bits', type=int, default=16)
    p.add_argument('--upload-mbps', type=float, default=0)
    a = p.parse_args()
    numbers = [a.audio_hours, a.asr_rtf, a.diar_rtf, a.secondary_rtf, a.retry_fraction, a.upload_mbps]
    if any(not math.isfinite(x) or x < 0 for x in numbers) or not 0 <= a.retry_fraction <= 1:
        p.error('inputs must be finite and non-negative; retry fraction must be in [0,1]')
    if min(a.sample_rate, a.channels, a.bits) <= 0:
        p.error('audio specifications must be positive')
    seconds = a.audio_hours * 3600
    pcm_bytes = seconds * a.sample_rate * a.channels * a.bits / 8
    compute = seconds * (a.asr_rtf + a.diar_rtf + a.secondary_rtf * a.retry_fraction)
    print(json.dumps(dict(assumptions_only=True, serial_compute_minutes=compute / 60,
                          uncompressed_pcm_megabytes=pcm_bytes / 1e6,
                          uncompressed_upload_minutes=(pcm_bytes*8/a.upload_mbps/1e6/60) if a.upload_mbps else None,
                          excluded='load, queue, download, report, layout, review, cleanup, retry-window overlap'), indent=2))


if __name__ == '__main__':
    main()
