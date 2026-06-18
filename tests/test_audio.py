import numpy as np
from smoco.audio import AudioFormat, AudioChunk, resample, to_mono, encode_s16le


def test_format_defaults_and_frame_sizes():
    fmt = AudioFormat()  # 16k mono S16LE 30ms
    assert fmt.sample_rate == 16000
    assert fmt.channels == 1
    assert fmt.sample_width == 2
    assert fmt.frame_samples() == 480          # 30ms @ 16k
    assert fmt.frame_bytes() == 960            # 480 * 2


def test_audio_chunk_is_immutable():
    c = AudioChunk(id="c1", pcm=b"\x00" * 960, start_time=0.0,
                   end_time=0.03, sample_rate=16000, is_final=True)
    assert c.id == "c1"
    try:
        c.id = "x"  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("AudioChunk should be frozen")


def test_to_mono_averages_stereo():
    stereo = np.array([[1.0, -1.0], [0.5, 0.5], [0.0, 0.0]], dtype=np.float32)
    mono = to_mono(stereo)
    assert mono.shape == (3,)
    np.testing.assert_allclose(mono, [0.0, 0.5, 0.0], atol=1e-6)


def test_to_mono_passes_through_mono():
    mono = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    out = to_mono(mono)
    assert out.shape == (3,)
    np.testing.assert_allclose(out, mono)


def test_resample_halves_rate():
    src = np.linspace(-1.0, 1.0, 4800, dtype=np.float32)  # 0.1s @ 48k
    out = resample(src, 48000, 16000)
    assert abs(len(out) - 1600) <= 2          # /3, tolerance


def test_encode_s16le_clips_and_round_trips():
    samples = np.array([0.0, 0.5, -0.5, 1.0, -1.0, 1.5], dtype=np.float32)
    raw = encode_s16le(samples)
    arr = np.frombuffer(raw, dtype="<i2")
    assert arr[0] == 0
    assert arr[3] == 32767                      # 1.0 -> full scale
    assert arr[5] == 32767                      # 1.5 clipped
