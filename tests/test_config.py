from smoco.config import Config, AudioFormat


def test_defaults_match_spec():
    c = Config()
    assert c.audio.sample_rate == 16000
    assert c.audio.frame_ms == 30
    assert c.silence_ms == 300
    assert c.max_chunk_ms == 15000
    assert c.min_chunk_ms == 200
    assert c.pad_ms == 50
    assert c.vad_aggressiveness == 2
    assert c.chunk_queue_size == 64
    assert c.transcriber_concurrency == 1
    assert c.shutdown_timeout == 5.0


def test_config_is_overridable():
    c = Config(silence_ms=500, max_chunk_ms=10000)
    assert c.silence_ms == 500
    assert c.max_chunk_ms == 10000
