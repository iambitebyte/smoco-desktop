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
