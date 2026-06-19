import numpy as np
import soundfile as sf
from smoco.audio import AudioFormat
from smoco.source.file import FileSource


def _write_wav(path, samples, sample_rate):
    # samples: mono float32 in [-1,1]
    sf.write(str(path), samples.astype(np.float32), sample_rate)


def test_reads_mono_16k_wav_in_30ms_frames(tmp_path):
    fmt = AudioFormat()
    n_frames = 10
    samples = np.ones(fmt.frame_samples() * n_frames, dtype=np.float32) * 0.1
    wav = tmp_path / "a.wav"
    _write_wav(wav, samples, 16000)

    src = FileSource(str(wav), target=fmt)
    src.start()
    got = []
    while (f := src.read_frame()) is not None:
        got.append(f)
    src.stop()

    assert len(got) == n_frames
    assert all(len(f) == fmt.frame_bytes() for f in got)


def test_resamples_48k_stereo_to_16k_mono(tmp_path):
    fmt = AudioFormat()
    # 48000 Hz, 30ms = 1440 samples stereo -> after /3 + downmix = 480 mono
    dur_frames = 5
    stereo = np.zeros((int(48000 * 0.03 * dur_frames), 2), dtype=np.float32)
    stereo[:, 0] = 0.2
    wav = tmp_path / "b.wav"
    _write_wav(wav, stereo, 48000)

    src = FileSource(str(wav), target=fmt)
    src.start()
    got = []
    while (f := src.read_frame()) is not None:
        got.append(f)
    src.stop()

    assert len(got) == dur_frames
    assert all(len(f) == fmt.frame_bytes() for f in got)


def test_partial_final_frame_is_dropped(tmp_path):
    fmt = AudioFormat()
    # 2.5 frames worth of samples -> 2 full frames, tail discarded
    n = int(fmt.frame_samples() * 2.5)
    samples = np.zeros(n, dtype=np.float32)
    wav = tmp_path / "c.wav"
    _write_wav(wav, samples, 16000)

    src = FileSource(str(wav), target=fmt)
    src.start()
    got = []
    while (f := src.read_frame()) is not None:
        got.append(f)
    src.stop()
    assert len(got) == 2
