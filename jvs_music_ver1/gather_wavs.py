import argparse
import collections
import contextlib
import os
import sys
import tempfile
import wave
from glob import glob
from os.path import islink
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
import webrtcvad
from tqdm.auto import tqdm


def get_parser():
    parser = argparse.ArgumentParser(
        description="Gather wav files",
    )
    parser.add_argument("in_dir", type=str, help="Input dir")
    parser.add_argument("--prefix", type=str, default="noname", help="Prefix")
    parser.add_argument(
        "--out_dir", type=str, default="data/acoustic/wav/", help="Output dir"
    )
    parser.add_argument("--run", action="store_true", help="I'm sure to run")
    parser.add_argument("--filters", type=str, nargs="+", help="Filters")
    parser.add_argument("--vad", action="store_true", help="VAD")
    return parser


def path2uttid(path):
    name = path.replace("/", "_")
    return name


def read_wave(path):
    with contextlib.closing(wave.open(path, "rb")) as wf:
        num_channels = wf.getnchannels()
        assert num_channels == 1
        sample_width = wf.getsampwidth()
        assert sample_width == 2
        sample_rate = wf.getframerate()
        assert sample_rate in (8000, 16000, 32000, 48000)
        pcm_data = wf.readframes(wf.getnframes())
        return pcm_data, sample_rate


def write_wave(path, audio, sample_rate):
    with contextlib.closing(wave.open(path, "wb")) as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio)


class Frame(object):
    def __init__(self, bytes, timestamp, duration):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration


def frame_generator(frame_duration_ms, audio, sample_rate):
    n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
    offset = 0
    timestamp = 0.0
    duration = (float(n) / sample_rate) / 2.0
    while offset + n < len(audio):
        yield Frame(audio[offset : offset + n], timestamp, duration)
        timestamp += duration
        offset += n


def vad_collector(sample_rate, frame_duration_ms, padding_duration_ms, vad, frames):
    num_padding_frames = int(padding_duration_ms / frame_duration_ms)
    # We use a deque for our sliding window/ring buffer.
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    # We have two states: TRIGGERED and NOTTRIGGERED. We start in the
    # NOTTRIGGERED state.
    triggered = False

    voiced_frames = []
    for frame in frames:
        is_speech = vad.is_speech(frame.bytes, sample_rate)

        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            # If we're NOTTRIGGERED and more than 90% of the frames in
            # the ring buffer are voiced frames, then enter the
            # TRIGGERED state.
            if num_voiced > 0.9 * ring_buffer.maxlen:
                triggered = True
                # We want to yield all the audio we see from now until
                # we are NOTTRIGGERED, but we have to start with the
                # audio that's already in the ring buffer.
                for f, s in ring_buffer:
                    voiced_frames.append(f)
                ring_buffer.clear()
        else:
            # We're in the TRIGGERED state, so collect the audio data
            # and add it to the ring buffer.
            voiced_frames.append(frame)
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            # If more than 90% of the frames in the ring buffer are
            # unvoiced, then enter NOTTRIGGERED and yield whatever
            # audio we've collected.
            if num_unvoiced > 0.9 * ring_buffer.maxlen:
                triggered = False
                yield b"".join([f.bytes for f in voiced_frames])
                ring_buffer.clear()
                voiced_frames = []
    # If we have any leftover voiced audio when we run out of input,
    # yield it.
    if voiced_frames:
        yield b"".join([f.bytes for f in voiced_frames])


def vad_segmentation(in_wav_path, out_dir, utt_id=None):
    audio, sample_rate = sf.read(in_wav_path)
    out_dir = Path(out_dir) if isinstance(out_dir, str) else out_dir
    out_dir.mkdir(exist_ok=True, parents=True)

    if len(audio.shape) == 2:
        audio = librosa.to_mono(audio.T)

    sample_rates = np.array([8000, 16000, 32000, 48000])

    if utt_id is None:
        utt_id = Path(in_wav_path).stem

    # not sure why but it sometimes fails with 48000
    # e.g., jsut-song_ver1
    if sample_rate not in sample_rates or sample_rate == 48000:
        orig_sr = sample_rate
        if sample_rate >= sample_rates[-1]:
            target_sample_rate = sample_rates[-1]
        else:
            target_sample_rate = sample_rates[sample_rates >= sample_rate][0]
        audio = librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sample_rate)
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            sf.write(f.name, audio, target_sample_rate, "PCM_16")

            audio, sample_rate = read_wave(f.name)

            vad = webrtcvad.Vad(3)
            frames = frame_generator(30, audio, sample_rate)
            frames = list(frames)
            segments = vad_collector(sample_rate, 30, 300, vad, frames)
            for i, segment in enumerate(segments):
                path = out_dir / f"{utt_id}_chunk-{i:002d}.wav"
                with tempfile.NamedTemporaryFile(suffix=".wav") as of:
                    write_wave(of.name, segment, sample_rate)

                    audio, sample_rate = sf.read(of.name)
                    assert sample_rate >= orig_sr
                    audio = librosa.resample(
                        audio, orig_sr=sample_rate, target_sr=orig_sr
                    )
                    if len(audio.shape) == 2:
                        audio = librosa.to_mono(audio.T)

                    sf.write(path, audio, orig_sr, "PCM_16")
    else:
        audio, sample_rate = read_wave(in_wav_path)
        vad = webrtcvad.Vad(3)
        frames = frame_generator(30, audio, sample_rate)
        frames = list(frames)
        segments = vad_collector(sample_rate, 30, 300, vad, frames)
        for i, segment in enumerate(segments):
            path = out_dir / f"{utt_id}_chunk-{i:002d}.wav"
            write_wave(path, segment, sample_rate)


if __name__ == "__main__":
    args = get_parser().parse_args(sys.argv[1:])

    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(exist_ok=True, parents=True)

    filters = args.filters if args.filters else []

    max_filename_length = 255
    for in_wav_path in tqdm(sorted(glob(f"{in_dir}/**/*.wav", recursive=True))):
        should_skip = False
        for filt in filters:
            if filt in in_wav_path:
                print("Skip", in_wav_path)
                should_skip = True
                continue
        if should_skip:
            continue

        path_from_dbroot = (
            Path(in_wav_path.replace(in_dir.as_posix(), "")).with_suffix("").as_posix()
        )
        if path_from_dbroot.startswith("/"):
            path_from_dbroot = path_from_dbroot[1:]

        utt_id = args.prefix + "_" + path2uttid(path_from_dbroot)

        if len(utt_id) > max_filename_length:
            print(utt_id, len(utt_id))

        if args.run:
            if args.vad:
                vad_segmentation(in_wav_path, out_dir, utt_id=utt_id)
            else:
                out_wav_path = (out_dir / utt_id).with_suffix(".wav")
                if (not out_wav_path.exists()) and (not islink(out_wav_path)):
                    os.symlink(in_wav_path, out_wav_path)
        else:
            x, sr = sf.read(in_wav_path)
            print(f"{utt_id}: {len(x) / sr:.2f} sec")
