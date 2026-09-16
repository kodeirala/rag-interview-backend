from io import BytesIO

from pypdf import PdfReader

from app.core.exceptions import EmptyDocumentError, UnsupportedFileTypeError


ALLOWED_EXTENSIONS = {".pdf", ".txt"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "application/octet-stream",
}


def normalize_extension(filename: str) -> str:
    name = filename.rsplit(".", 1)
    if len(name) != 2:
        raise UnsupportedFileTypeError()
    return f".{name[1].lower()}"


def extract_text(filename: str, content: bytes) -> str:
    extension = normalize_extension(filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError()

    if extension == ".txt":
        text = _decode_text(content)
    else:
        text = _extract_pdf(content)

    cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not cleaned:
        raise EmptyDocumentError()
    return cleaned


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _extract_pdf(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    pages: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        pages.append(page_text)
    return "\n".join(pages)
