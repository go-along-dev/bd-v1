from sqlalchemy import (
    Column, String, Text,
    DateTime, ForeignKey, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.postgres import Base


class DriverDocument(Base):
    __tablename__ = "driver_documents"

    # ─── Primary Key ──────────────────────────
    id          = Column(
                    UUID(as_uuid=True),
                    primary_key=True,
                    server_default=func.gen_random_uuid()
                )

    # ─── Driver ───────────────────────────────
    driver_id   = Column(
                    UUID(as_uuid=True),
                    ForeignKey("drivers.id", ondelete="CASCADE"),
                    nullable=False
                )

    # ─── Document ─────────────────────────────
    doc_type    = Column(String(30), nullable=False)
    # license | rc_book | insurance | permit

    file_url    = Column(Text, nullable=False)
    # Supabase Storage signed URL or path

    # ─── Status ───────────────────────────────
    status      = Column(
                    String(20),
                    nullable=False,
                    default="pending"
                )
    # pending → approved → rejected

    # ─── Timestamps ───────────────────────────
    created_at  = Column(DateTime(timezone=True),
                    nullable=False, server_default=func.now())

    # ─── Constraints ──────────────────────────
    __table_args__ = (
        CheckConstraint(
            "doc_type IN ('license', 'rc_book', 'insurance', 'permit')",
            name="ck_driver_docs_type"
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_driver_docs_status"
        ),
    )

    # ─── Relationships ────────────────────────
    driver      = relationship("Driver", back_populates="documents")