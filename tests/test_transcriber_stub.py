import asyncio
import os
from smoco.audio import AudioChunk, AudioFormat
from smoco.transcriber.stub import StubTranscriber


def test_stub_returns_empty_result_and_is_final():
    tr = StubTranscriber()
    chunk = AudioChunk(id="x", pcm=b"\x00" * 960, start_time=0.0,
                       end_time=0.03, sample_rate=16000, is_final=True)
    result = asyncio.run(tr.transcribe(chunk))
    assert result["chunk_id"] == "x"
    assert result["text"] == ""
    assert result["is_final"] is True
    assert result["error"] is None
    asyncio.run(tr.close())


def test_stub_writes_wav_when_outdir_set(tmp_path):
    tr = StubTranscriber(out_dir=str(tmp_path))
    chunk = AudioChunk(id="c7", pcm=b"\x01" * 960, start_time=1.0,
                       end_time=1.03, sample_rate=16000, is_final=True)
    asyncio.run(tr.transcribe(chunk))
    asyncio.run(tr.close())
    written = list(tmp_path.glob("c7*.wav"))
    assert len(written) == 1
    assert os.path.getsize(written[0]) > 0
