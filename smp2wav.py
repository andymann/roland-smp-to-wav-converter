#!/usr/bin/env python3
"""
Convert a Roland SP-404 mk2 internal .SMP sample file to a standard .WAV file.

Reverse-engineered container format ("RFWV"):
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

NOTE: The 481-byte "leader" size was determined from a single sample
pair. If conversions of other .SMP files sound wrong at the very
start, try adjusting LEADER_SIZE below.
"""
mport struct
import sys
import wave

HEADER_SIZE = 32
LEADER_SIZE = 481          # empirically determined "junk" block after the header
DATA_START = HEADER_SIZE + LEADER_SIZE  # = 513


def convert_smp_to_wav(smp_path: str, wav_path: str) -> None:
    with open(smp_path, "rb") as f:
        raw = f.read()

    magic = raw[0:4]
    if magic != b"RFWV":
        raise ValueError(f"Not a recognized SMP file (magic={magic!r})")

    _size_field, sample_rate, channels, bits = struct.unpack(">4I", raw[4:20])
    bytes_per_sample = bits // 8
    frame_size = bytes_per_sample * channels

    pcm = raw[DATA_START:]

    # Drop a trailing partial frame, if any (the SMP body isn't always
    # an exact multiple of the frame size at the very end).
    usable_len = (len(pcm) // frame_size) * frame_size
    if usable_len != len(pcm):
        pcm = pcm[:usable_len]

    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(bytes_per_sample)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)

    print(f"OK: {sample_rate} Hz, {channels} ch, {bits}-bit -> {wav_path}")
    print(f"  {len(pcm) // frame_size} frames ({len(pcm) / frame_size / sample_rate:.3f} s)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} input.SMP output.wav")
        sys.exit(1)
    convert_smp_to_wav(sys.argv[1], sys.argv[2])
