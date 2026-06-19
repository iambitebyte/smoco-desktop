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
