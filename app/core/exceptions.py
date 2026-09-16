"""Domain exceptions mapped to HTTP responses."""


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class UnsupportedFileTypeError(AppError):
    def __init__(self) -> None:
        super().__init__("Only .pdf and .txt uploads are supported", status_code=415)


class FileTooLargeError(AppError):
    def __init__(self, max_bytes: int) -> None:
        super().__init__(
            f"File exceeds maximum size of {max_bytes} bytes",
            status_code=413,
        )


class EmptyDocumentError(AppError):
    def __init__(self) -> None:
        super().__init__("No extractable text found in the uploaded file", status_code=422)


class LLMNotConfiguredError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "OPENAI_API_KEY is required for embeddings and chat",
            status_code=503,
        )
