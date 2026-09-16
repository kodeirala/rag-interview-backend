from app.core.config import Settings
from app.services.chunking import chunk_text


def test_fixed_size_respects_overlap() -> None:
    settings = Settings(chunk_size=20, chunk_overlap=5)
    text = "alpha bravo charlie delta echo foxtrot golf hotel"
    chunks = chunk_text(text, "fixed_size", settings)
    assert len(chunks) >= 2
    assert chunks[0].index == 0
    assert all(chunk.text for chunk in chunks)


def test_sentence_window_builds_sliding_groups() -> None:
    settings = Settings(sentence_window_size=2, sentence_window_overlap=1)
    text = "One sentence. Two sentence. Three sentence. Four sentence."
    chunks = chunk_text(text, "sentence_window", settings)
    assert len(chunks) >= 3
    assert "One sentence." in chunks[0].text
    assert "Two sentence." in chunks[0].text
