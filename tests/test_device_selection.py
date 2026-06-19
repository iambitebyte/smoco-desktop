import pytest
from smoco.__main__ import pick_device

DEVS = [
    {"index": 5, "name": "Speakers", "sample_rate": 48000, "channels": 2, "is_default": True},
    {"index": 9, "name": "Headphones", "sample_rate": 48000, "channels": 2, "is_default": False},
]


def test_empty_choice_returns_default_index():
    assert pick_device(DEVS, "") == 5


def test_numeric_choice_returns_device_index():
    assert pick_device(DEVS, "1") == 5
    assert pick_device(DEVS, "2") == 9


def test_whitespace_only_choice_returns_default():
    assert pick_device(DEVS, "   ") == 5


def test_out_of_range_raises():
    with pytest.raises(ValueError):
        pick_device(DEVS, "0")
    with pytest.raises(ValueError):
        pick_device(DEVS, "3")


def test_non_numeric_raises():
    with pytest.raises(ValueError):
        pick_device(DEVS, "abc")


def test_empty_devices_raises():
    with pytest.raises(ValueError):
        pick_device([], "1")


def test_no_default_and_empty_choice_raises():
    devs = [{"index": 1, "name": "x", "sample_rate": 48000, "channels": 2, "is_default": False}]
    with pytest.raises(ValueError):
        pick_device(devs, "")


from smoco.__main__ import _prompt_for_device


def test_prompt_first_try_valid(capsys):
    inputs = iter(["2"])
    idx = _prompt_for_device(DEVS, input_fn=lambda _p: next(inputs))
    assert idx == 9
    out = capsys.readouterr().out
    assert "Headphones" in out
    assert "*" in out  # 默认设备标记


def test_prompt_retries_then_succeeds(capsys):
    inputs = iter(["abc", "99", "1"])
    idx = _prompt_for_device(DEVS, input_fn=lambda _p: next(inputs), max_tries=3)
    assert idx == 5


def test_prompt_exhausts_tries_returns_none(capsys):
    inputs = iter(["x", "y", "z"])
    idx = _prompt_for_device(DEVS, input_fn=lambda _p: next(inputs), max_tries=3)
    assert idx is None


def test_prompt_eof_returns_none(capsys):
    def boom(_p):
        raise EOFError
    idx = _prompt_for_device(DEVS, input_fn=boom)
    assert idx is None


from smoco.__main__ import _resolve_device, _build_parser


class _Args:
    def __init__(self, device):
        self.device = device


def test_resolve_device_explicit_arg_skips_prompt():
    assert _resolve_device(_Args(device=7), list_devices_fn=lambda: DEVS,
                            input_fn=lambda _p: pytest.fail("不应提示")) == 7


def test_resolve_device_interactive_uses_prompt(capsys):
    idx = _resolve_device(_Args(device=None), list_devices_fn=lambda: DEVS,
                          input_fn=lambda _p: "2")
    assert idx == 9


def test_resolve_device_empty_list_returns_none(capsys):
    assert _resolve_device(_Args(device=None), list_devices_fn=lambda: []) is None


def test_resolve_device_prompt_exhausted_returns_none(capsys):
    inputs = iter(["x", "y", "z"])
    assert _resolve_device(_Args(device=None), list_devices_fn=lambda: DEVS,
                           input_fn=lambda _p: next(inputs)) is None


def test_cmd_run_wasapi_uses_selected_device(monkeypatch):
    import smoco.__main__ as cli
    import smoco.source.wasapi as wav
    captured = {}

    class FakeSource:
        list_devices = staticmethod(lambda: DEVS)

        def __init__(self, target=None, device_index=None):
            captured["device_index"] = device_index

    class FakePipeline:
        def __init__(self, *a, **k):
            self.error = None

        async def run(self):
            return None

    monkeypatch.setattr(wav, "_AVAILABLE", True)
    monkeypatch.setattr(wav, "WASAPILoopbackSource", FakeSource)
    monkeypatch.setattr(cli, "Pipeline", FakePipeline)
    monkeypatch.setattr("builtins.input", lambda _p: "2")

    args = _build_parser().parse_args(["run", "--wasapi"])
    assert cli.cmd_run(args) == 0
    assert captured["device_index"] == 9


def test_cmd_run_wasapi_device_flag_skips_prompt(monkeypatch):
    import smoco.__main__ as cli
    import smoco.source.wasapi as wav
    captured = {}

    class FakeSource:
        list_devices = staticmethod(lambda: DEVS)

        def __init__(self, target=None, device_index=None):
            captured["device_index"] = device_index

    class FakePipeline:
        def __init__(self, *a, **k):
            self.error = None

        async def run(self):
            return None

    monkeypatch.setattr(wav, "_AVAILABLE", True)
    monkeypatch.setattr(wav, "WASAPILoopbackSource", FakeSource)
    monkeypatch.setattr(cli, "Pipeline", FakePipeline)
    monkeypatch.setattr("builtins.input", lambda _p: pytest.fail("不应提示"))

    args = _build_parser().parse_args(["run", "--wasapi", "--device", "5"])
    assert cli.cmd_run(args) == 0
    assert captured["device_index"] == 5


def test_cmd_run_wasapi_no_devices_returns_1(monkeypatch, capsys):
    import smoco.__main__ as cli
    import smoco.source.wasapi as wav

    class FakeSource:
        list_devices = staticmethod(lambda: [])

    monkeypatch.setattr(wav, "_AVAILABLE", True)
    monkeypatch.setattr(wav, "WASAPILoopbackSource", FakeSource)
    args = _build_parser().parse_args(["run", "--wasapi"])
    assert cli.cmd_run(args) == 1
    assert "找不到" in capsys.readouterr().out
