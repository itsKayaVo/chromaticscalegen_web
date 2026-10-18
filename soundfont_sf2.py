"""Write an SF2 bank with one mapped sample per generated note and edge zones."""

from __future__ import annotations

import struct
import wave
from pathlib import Path
from typing import Sequence


def _chunk(tag: bytes, payload: bytes) -> bytes:
    padding = b"\0" if len(payload) & 1 else b""
    return tag + struct.pack("<I", len(payload)) + payload + padding


def _list(kind: bytes, payload: bytes) -> bytes:
    return _chunk(b"LIST", kind + payload)


def _fixed_name(value: str, size: int) -> bytes:
    return value.encode("ascii", errors="replace")[:size].ljust(size, b"\0")


def _wav_pcm16(path: Path) -> tuple[int, bytes]:
    with wave.open(str(path), "rb") as wav_file:
        if wav_file.getcomptype() != "NONE":
            raise ValueError(f"SoundFont export requires uncompressed WAV audio: {path.name}")
        channels = wav_file.getnchannels()
        width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frames = wav_file.readframes(wav_file.getnframes())

    if channels < 1 or sample_rate < 1:
        raise ValueError(f"Invalid WAV format for SoundFont export: {path.name}")
    if width not in (1, 2, 3, 4):
        raise ValueError(f"Unsupported WAV bit depth for SoundFont export: {path.name}")

    values: list[int] = []
    if width == 1:
        values = [(sample - 128) << 8 for sample in frames]
    elif width == 2:
        count = len(frames) // 2
        values = [item[0] for item in struct.iter_unpack("<h", frames[: count * 2])]
    elif width == 3:
        for offset in range(0, len(frames) - 2, 3):
            sample = frames[offset] | (frames[offset + 1] << 8) | (frames[offset + 2] << 16)
            if sample & 0x800000:
                sample -= 0x1000000
            values.append(sample >> 8)
    else:
        count = len(frames) // 4
        values = [item[0] >> 16 for item in struct.iter_unpack("<i", frames[: count * 4])]

    if channels > 1:
        values = [sum(values[offset : offset + channels]) // channels
                  for offset in range(0, len(values) - channels + 1, channels)]
    if not values:
        raise ValueError(f"WAV sample is empty: {path.name}")
    pcm16 = struct.pack(f"<{len(values)}h", *(max(-32768, min(32767, value)) for value in values))
    return sample_rate, pcm16


def create_soundfont(
    output_path: Path,
    sample_paths: Sequence[Path],
    start_midi: int,
    preset_name: str = "Chromatic Scale",
) -> None:
    """Create a bank mapping rendered notes, with edge samples covering MIDI 0–127."""
    if not sample_paths:
        raise ValueError("No note samples are available for SoundFont export.")
    if start_midi < 0 or start_midi + len(sample_paths) - 1 > 127:
        raise ValueError("SoundFont note range must fit within MIDI notes 0–127.")

    sample_data = bytearray()
    sample_headers: list[bytes] = []
    instrument_generators: list[bytes] = []
    instrument_bags: list[bytes] = []
    current_sample_offset = 0
    current_generator_index = 0

    for index, path in enumerate(sample_paths):
        midi_note = start_midi + index
        # Extend the outermost zones so FL Studio Mobile can play beyond the
        # generated range by transposing the nearest available edge sample.
        low_key = 0 if index == 0 else midi_note
        high_key = 127 if index == len(sample_paths) - 1 else midi_note
        sample_rate, pcm16 = _wav_pcm16(Path(path))
        frame_count = len(pcm16) // 2
        if frame_count < 1:
            raise ValueError(f"WAV sample is empty: {Path(path).name}")
        start = current_sample_offset
        end = start + frame_count
        note_name = f"Note_{midi_note:03d}"
        sample_headers.append(
            struct.pack(
                "<20sIIIIIBbHH",
                _fixed_name(note_name, 20),
                start,
                end,
                start,
                end,
                sample_rate,
                midi_note,
                0,
                0,
                1,
            )
        )
        instrument_generators.extend(
            (
                struct.pack("<HH", 43, low_key | (high_key << 8)),
                struct.pack("<HH", 58, midi_note),
                struct.pack("<HH", 53, index),
            )
        )
        instrument_bags.append(struct.pack("<HH", current_generator_index, 0))
        current_generator_index += 3
        sample_data.extend(pcm16)
        sample_data.extend(b"\0" * (46 * 2))
        current_sample_offset = end + 46

    instrument_bags.append(struct.pack("<HH", current_generator_index, 0))
    sample_headers.append(
        struct.pack(
            "<20sIIIIIBbHH",
            _fixed_name("EOS", 20),
            current_sample_offset,
            current_sample_offset,
            current_sample_offset,
            current_sample_offset,
            44100,
            0,
            0,
            0,
            0,
        )
    )

    info = b"".join(
        (
            _chunk(b"ifil", struct.pack("<HH", 2, 1)),
            _chunk(b"isng", b"EMU8000\0"),
            _chunk(b"INAM", preset_name.encode("ascii", errors="replace") + b"\0"),
            _chunk(b"ISFT", b"Chromatic Scale Generator\0"),
        )
    )
    sdta = _chunk(b"smpl", bytes(sample_data))

    preset_header = struct.pack(
        "<20sHHHIII", _fixed_name(preset_name, 20), 0, 0, 0, 0, 0, 0
    )
    terminal_preset_header = struct.pack(
        "<20sHHHIII", _fixed_name("EOP", 20), 0, 0, 1, 0, 0, 0
    )
    preset_bags = struct.pack("<HHHH", 0, 0, 1, 0)
    preset_modulators = b"\0" * 10
    preset_generators = struct.pack("<HH", 41, 0)
    instrument_header = struct.pack("<20sH", _fixed_name(preset_name, 20), 0)
    terminal_instrument_header = struct.pack(
        "<20sH", _fixed_name("EOI", 20), len(sample_paths)
    )
    instrument_modulators = b"\0" * 10
    pdta = b"".join(
        (
            _chunk(b"phdr", preset_header + terminal_preset_header),
            _chunk(b"pbag", preset_bags),
            _chunk(b"pmod", preset_modulators),
            _chunk(b"pgen", preset_generators),
            _chunk(b"inst", instrument_header + terminal_instrument_header),
            _chunk(b"ibag", b"".join(instrument_bags)),
            _chunk(b"imod", instrument_modulators),
            _chunk(b"igen", b"".join(instrument_generators)),
            _chunk(b"shdr", b"".join(sample_headers)),
        )
    )
    body = b"sfbk" + _list(b"INFO", info) + _list(b"sdta", sdta) + _list(b"pdta", pdta)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)
