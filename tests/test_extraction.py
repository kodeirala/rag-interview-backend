import pytest

from app.core.exceptions import EmptyDocumentError, UnsupportedFileTypeError
from app.services.extraction import extract_text


def test_extract_txt() -> None:
    text = extract_text("notes.txt", b"Hello interview world\n\nSecond line")
    assert "Hello interview world" in text
    assert "Second line" in text


def test_rejects_unsupported_extension() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        extract_text("notes.docx", b"data")


def test_rejects_empty_text() -> None:
    with pytest.raises(EmptyDocumentError):
        extract_text("empty.txt", b"   \n  ")
