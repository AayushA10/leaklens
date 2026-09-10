from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.db import Base


def utc_now():
    return datetime.now(timezone.utc)


class Report(Base):
    __tablename__ = "reports"

    report_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        index=True,
    )

    website_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    final_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    website_title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Complete scanner result stored as JSON text.
    # This lets us preserve the current report structure
    # without rewriting the scanner/payment/PDF code.
    report_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # AI result is kept separately so it can be generated
    # after payment and cached permanently.
    ai_analysis_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_paid: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    stripe_session_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )

    stripe_payment_intent_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    customer_email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
    )

    payment_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="unpaid",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self):
        return (
            f"<Report "
            f"report_id={self.report_id!r} "
            f"is_paid={self.is_paid}>"
        )