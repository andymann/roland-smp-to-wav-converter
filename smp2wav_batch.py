#!/usr/bin/env python3
"""
Recursively convert Roland SP-404 mk2 internal .SMP sample files to
standard .WAV files.

Usage:
    python3 smp2wav_batch.py <source_dir> <output_dir>

Walks <source_dir> recursively, finds every *.SMP / *.smp file, and
writes a converted .wav for each one into <output_dir>, mirroring the
original folder structure.

Format notes (reverse-engineered "RFWV" container):
  offset 0   : magic "RFWV"
  offset 4   : uint32 BE, filesize - 8
  offset 8   : uint32 BE, sample rate
  offset 12  : uint32 BE, channel count
  offset 16  : uint32 BE, bits per sample
  offset 20  : uint32 BE, reserved (0)
  offset 24  : 8 bytes padding
  offset 32  : ~481 bytes of leftover/garbage data from the sampler's
               internal buffer (not part of the actual sample)
  offset 513 : raw interleaved little-endian PCM audio data (to EOF)

NOTE: LEADER_SIZE was determined from a single sample pair. If a
converted file sounds wrong at the very start, try adjusting it below.
"""

import argparse
import struct
import sys
import wave
from pathlib import Path

HEADER_SIZE = 32
LEADER_SIZE = 481          # empirically determined "junk" block after the header
DATA_START = HEADER_SIZE + LEADER_SIZE  # = 513


def convert_smp_to_wav(smp_path: Path, wav_path: Path) -> None:
    raw = smp_path.read_bytes()

    magic = raw[0:4]
    if magic != b"RFWV":
        raise ValueError(f"not a recognized SMP file (magic={magic!r})")

    _size_field, sample_rate, channels, bits = struct.unpack(">4I", raw[4:20])
    bytes_per_sample = bits // 8
    frame_size = bytes_per_sample * channels

    pcm = raw[DATA_START:]

    # Drop a trailing partial frame, if any.
    usable_len = (len(pcm) // frame_size) * frame_size
    if usable_len != len(pcm):
        pcm = pcm[:usable_len]

    wav_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(bytes_per_sample)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recursively convert .SMP files to .WAV files."
    )
    parser.add_argument("source_dir", type=Path, help="Directory to search for .SMP files")
    parser.add_argument("output_dir", type=Path, help="Directory to write converted .wav files into")
    args = parser.parse_args()

    source_dir: Path = args.source_dir
    output_dir: Path = args.output_dir

    if not source_dir.is_dir():
        print(f"Error: source path '{source_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    smp_files = sorted(
        p for p in source_dir.rglob("*") if p.is_file() and p.suffix.lower() == ".smp"
    )

    if not smp_files:
        print(f"No .SMP files found under '{source_dir}'")
        return

    converted = 0
    failed = 0

    for smp_path in smp_files:
        rel_path = smp_path.relative_to(source_dir)
        wav_path = output_dir / rel_path.with_suffix(".wav")

        try:
            convert_smp_to_wav(smp_path, wav_path)
            print(f"OK   {rel_path} -> {wav_path.relative_to(output_dir)}")
            converted += 1
        except Exception as e:
            print(f"FAIL {rel_path}: {e}", file=sys.stderr)
            failed += 1

    print(f"\nDone: {converted} converted, {failed} failed, {len(smp_files)} total")


if __name__ == "__main__":
    main()
