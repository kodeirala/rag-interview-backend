import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    chunking_strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    qdrant_point_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    preview: Mapped[str] = mapped_column(Text, nullable=False)

    document: Mapped[Document] = relationship(back_populates="chunks")


class InterviewBooking(Base):
    __tablename__ = "interview_bookings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    email_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    interview_date: Mapped[str] = mapped_column(String(32), nullable=False)
    interview_time: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
