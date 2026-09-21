from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
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

class MonitoredSite(Base):
    __tablename__ = "monitored_sites"

    site_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        index=True,
    )

    website_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    website_title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    owner_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    monitoring_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    scan_frequency: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="daily",
    )

    last_scanned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    next_scan_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
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

    def __repr__(self):
        return (
            f"<MonitoredSite "
            f"site_id={self.site_id!r} "
            f"monitoring_enabled={self.monitoring_enabled}>"
        )


class ScanSnapshot(Base):
    __tablename__ = "scan_snapshots"

    snapshot_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        index=True,
    )

    site_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("monitored_sites.site_id"),
        nullable=False,
        index=True,
    )

    report_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )

    def __repr__(self):
        return (
            f"<ScanSnapshot "
            f"snapshot_id={self.snapshot_id!r} "
            f"site_id={self.site_id!r}>"
        )


class LeakIssue(Base):
    __tablename__ = "leak_issues"

    __table_args__ = (
        UniqueConstraint(
            "site_id",
            "fingerprint",
            name="uq_leak_issues_site_fingerprint",
        ),
    )

    issue_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        index=True,
    )

    site_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("monitored_sites.site_id"),
        nullable=False,
        index=True,
    )

    fingerprint: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    issue_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    severity: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    recommendation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="open",
        index=True,
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self):
        return (
            f"<LeakIssue "
            f"issue_id={self.issue_id!r} "
            f"status={self.status!r}>"
        )


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    # Clerk user ID. One subscription per LeakLens user.
    user_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )

    # free | starter | growth | pro
    plan: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="free",
        index=True,
    )

    # active | canceled | past_due
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
        index=True,
    )

    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )

    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )

    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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


class MonthlyUsage(Base):
    __tablename__ = "monthly_usage"

    # Example: clerk_user_id:2026-09
    usage_id: Mapped[str] = mapped_column(
        String(320),
        primary_key=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # YYYY-MM
    billing_month: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        index=True,
    )

    manual_scans: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    ai_analyses: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
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
