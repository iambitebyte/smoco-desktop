import numpy as np
from smoco.audio import AudioFormat
from smoco.source.metering import MeteringSource


class _FakeSource:
    def __init__(self, frames, fmt):
        self._frames = list(frames)
        self._i = 0
        self.audio_format = fmt
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def read_frame(self):
        if self._i >= len(self._frames):
            return None
        f = self._frames[self._i]
        self._i += 1
        return f


_FMT = AudioFormat()


def _full_frame():
    return np.full(_FMT.frame_samples(), 32767, dtype="<i2").tobytes()


def _silent_frame():
    return b"\x00" * _FMT.frame_bytes()


def test_metering_updates_rms_and_passes_through():
    src = _FakeSource([_full_frame(), _silent_frame()], _FMT)
    m = MeteringSource(src)
    m.start()
    assert src.started
    f1 = m.read_frame()
    assert f1 == _full_frame()              # 帧原样透传
    assert m.latest_rms > 0.9
    assert abs(m.latest_peak - m.latest_rms) < 1e-6
    m.read_frame()                          # 静音帧
    assert m.latest_rms == 0.0
    assert m.latest_peak > 0.9             # peak 不衰减
    assert m.read_frame() is None          # 源结束
    m.stop()
    assert src.stopped


def test_metering_delegates_audio_format():
    src = _FakeSource([], _FMT)
    m = MeteringSource(src)
    assert m.audio_format is _FMT


def test_metering_none_frame_keeps_levels():
    src = _FakeSource([], _FMT)
    m = MeteringSource(src)
    assert m.read_frame() is None
    assert m.latest_rms == 0.0
    assert m.latest_peak == 0.0


from smoco.__main__ import meter_bar


def test_meter_bar_empty():
    assert meter_bar(0.0) == "[" + "░" * 24 + "]"


def test_meter_bar_full():
    assert meter_bar(1.0) == "[" + "█" * 24 + "]"


def test_meter_bar_half():
    bar = meter_bar(0.5, width=24)
    assert bar.count("█") == 12
    assert bar.count("░") == 12


def test_meter_bar_clamps_out_of_range():
    assert meter_bar(-0.5) == "[" + "░" * 24 + "]"
    assert meter_bar(1.5) == "[" + "█" * 24 + "]"


import asyncio
from smoco.__main__ import _run_with_meter


def test_run_with_meter_no_meter_just_runs_pipe():
    ran = []

    class FakePipe:
        error = None

        async def run(self):
            ran.append(True)

    asyncio.run(_run_with_meter(FakePipe(), None, meter=False))
    assert ran == [True]


def test_run_with_meter_renders_and_completes(capsys):
    class FakeSrc:
        audio_format = _FMT

        def start(self):
            pass

        def stop(self):
            pass

        def read_frame(self):
            return None

    class FakePipe:
        error = None

        async def run(self):
            await asyncio.sleep(0.1)   # 让渲染协程至少画一帧

    src = MeteringSource(FakeSrc())
    asyncio.run(_run_with_meter(FakePipe(), src, meter=True))
    out = capsys.readouterr().out
    assert "rms=" in out
    assert out.endswith("\n")           # 收尾换行


def test_cmd_run_file_meter_shows_bar(tmp_path, capsys):
    import soundfile as sf
    from smoco.__main__ import cmd_run, _build_parser

    wav = tmp_path / "a.wav"
    sf.write(str(wav),
             (np.random.RandomState(0).uniform(-0.5, 0.5, 16000)).astype("float32"),
             16000)
    args = _build_parser().parse_args(["run", "--file", str(wav), "--meter"])
    assert cmd_run(args) == 0
    assert "rms=" in capsys.readouterr().out
