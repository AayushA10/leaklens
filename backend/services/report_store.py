import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError

from database.db import SessionLocal
from database.models import Report


def _json_dumps(data: dict) -> str:
    """
    Convert Python dictionary to JSON text for database storage.
    """
    return json.dumps(
        data,
        ensure_ascii=False,
    )


def _json_loads(data: Optional[str]) -> Optional[dict]:
    """
    Safely convert stored JSON text back into a dictionary.
    """
    if not data:
        return None

    try:
        result = json.loads(data)

        if isinstance(result, dict):
            return result

        return None

    except (json.JSONDecodeError, TypeError):
        return None


def _sync_model_metadata(
    db_report: Report,
    report: dict,
) -> None:
    """
    Keep useful searchable database columns synchronized
    with the full report JSON.
    """

    website = report.get("website") or {}
    payment = report.get("payment") or {}

    db_report.website_url = (
        website.get("url")
        or report.get("url")
        or report.get("website_url")
    )

    db_report.final_url = (
        website.get("final_url")
        or website.get("url")
        or report.get("final_url")
    )

    db_report.website_title = (
        website.get("title")
        or report.get("title")
    )

    payment_status = (
        payment.get("status")
        or "unpaid"
    )

    db_report.payment_status = payment_status
    db_report.is_paid = payment_status == "paid"

    db_report.stripe_session_id = (
        payment.get("checkout_session_id")
    )

    db_report.stripe_payment_intent_id = (
        payment.get("payment_intent_id")
    )

    db_report.customer_email = (
        payment.get("customer_email")
    )

    paid_at = payment.get("paid_at")

    if paid_at:
        try:
            db_report.paid_at = datetime.fromisoformat(
                paid_at.replace(
                    "Z",
                    "+00:00",
                )
            )
        except (ValueError, TypeError):
            pass

def save_report(
    report: dict,
) -> str:
    """
    Save a new LeakLens report in the database
    and return a unique report ID.
    """

    report_id = str(
        uuid.uuid4()
    )

    db = SessionLocal()

    try:
        report_copy = dict(report)

        ai_analysis = report_copy.get(
            "ai_analysis"
        )

        db_report = Report(
            report_id=report_id,
            report_json=_json_dumps(
                report_copy
            ),
            ai_analysis_json=(
                _json_dumps(ai_analysis)
                if isinstance(
                    ai_analysis,
                    dict,
                )
                else None
            ),
            is_paid=False,
            payment_status="unpaid",
        )

        _sync_model_metadata(
            db_report,
            report_copy,
        )

        db.add(
            db_report
        )

        db.commit()

        return report_id

    except SQLAlchemyError:
        db.rollback()
        raise

    finally:
        db.close()


def get_report(
    report_id: str,
) -> Optional[dict]:
    """
    Retrieve a previously stored report
    from the database.
    """

    db = SessionLocal()

    try:
        db_report = db.get(
            Report,
            report_id,
        )

        if not db_report:
            return None

        report = _json_loads(
            db_report.report_json
        )

        if report is None:
            return None

        # Keep AI analysis available in the same place
        # expected by the existing application.
        if (
            db_report.ai_analysis_json
            and not report.get(
                "ai_analysis"
            )
        ):
            ai_analysis = _json_loads(
                db_report.ai_analysis_json
            )

            if ai_analysis:
                report["ai_analysis"] = (
                    ai_analysis
                )

        # Rebuild payment data from dedicated DB columns.
        # This also makes the DB columns authoritative for
        # whether a report is actually unlocked.
        payment = report.get(
            "payment"
        ) or {}

        payment["status"] = (
            db_report.payment_status
            or (
                "paid"
                if db_report.is_paid
                else "unpaid"
            )
        )

        if db_report.stripe_session_id:
            payment[
                "checkout_session_id"
            ] = db_report.stripe_session_id

        if db_report.stripe_payment_intent_id:
            payment[
                "payment_intent_id"
            ] = (
                db_report
                .stripe_payment_intent_id
            )

        if db_report.customer_email:
            payment[
                "customer_email"
            ] = db_report.customer_email

        if db_report.paid_at:
            payment["paid_at"] = (
                db_report.paid_at.isoformat()
            )

        report["payment"] = payment

        return report

    except SQLAlchemyError:
        return None

    finally:
        db.close()


def update_report(
    report_id: str,
    report: dict,
) -> bool:
    """
    Replace an existing report while preserving
    the current report_store API.
    """

    db = SessionLocal()

    try:
        db_report = db.get(
            Report,
            report_id,
        )

        if not db_report:
            return False

        db_report.report_json = (
            _json_dumps(report)
        )

        ai_analysis = report.get(
            "ai_analysis"
        )

        if isinstance(
            ai_analysis,
            dict,
        ):
            db_report.ai_analysis_json = (
                _json_dumps(
                    ai_analysis
                )
            )

        _sync_model_metadata(
            db_report,
            report,
        )

        db_report.updated_at = (
            datetime.now(
                timezone.utc
            )
        )

        db.commit()

        return True

    except SQLAlchemyError:
        db.rollback()
        return False

    finally:
        db.close()


def save_ai_analysis(
    report_id: str,
    analysis: dict,
) -> bool:
    """
    Store Groq AI analysis for an existing report.
    """

    db = SessionLocal()

    try:
        db_report = db.get(
            Report,
            report_id,
        )

        if not db_report:
            return False

        report = _json_loads(
            db_report.report_json
        )

        if report is None:
            return False

        report["ai_analysis"] = analysis

        db_report.ai_analysis_json = (
            _json_dumps(
                analysis
            )
        )

        db_report.report_json = (
            _json_dumps(
                report
            )
        )

        db_report.updated_at = (
            datetime.now(
                timezone.utc
            )
        )

        db.commit()

        return True

    except SQLAlchemyError:
        db.rollback()
        return False

    finally:
        db.close()


def save_checkout_session(
    report_id: str,
    session_id: str,
) -> bool:
    """
    Save the latest Stripe Checkout Session ID
    for the report.
    """

    db = SessionLocal()

    try:
        db_report = db.get(
            Report,
            report_id,
        )

        if not db_report:
            return False

        report = _json_loads(
            db_report.report_json
        )

        if report is None:
            return False

        payment = report.get(
            "payment"
        ) or {}

        payment["status"] = (
            payment.get("status")
            or "unpaid"
        )

        payment[
            "checkout_session_id"
        ] = session_id

        report["payment"] = payment

        db_report.stripe_session_id = (
            session_id
        )

        db_report.payment_status = (
            payment["status"]
        )

        db_report.is_paid = (
            payment["status"]
            == "paid"
        )

        db_report.report_json = (
            _json_dumps(
                report
            )
        )

        db_report.updated_at = (
            datetime.now(
                timezone.utc
            )
        )

        db.commit()

        return True

    except SQLAlchemyError:
        db.rollback()
        return False

    finally:
        db.close()


def mark_report_paid(
    report_id: str,
    session_id: str,
    payment_intent_id: Optional[str] = None,
    customer_email: Optional[str] = None,
) -> bool:
    """
    Mark a report as paid after Stripe confirms payment.

    Safe to call multiple times because Stripe webhooks
    may retry the same event.
    """

    db = SessionLocal()

    try:
        db_report = db.get(
            Report,
            report_id,
        )

        if not db_report:
            return False

        report = _json_loads(
            db_report.report_json
        )

        if report is None:
            return False

        paid_at = datetime.now(
            timezone.utc
        )

        payment = report.get(
            "payment"
        ) or {}

        payment.update(
            {
                "status": "paid",
                "checkout_session_id": (
                    session_id
                ),
                "payment_intent_id": (
                    payment_intent_id
                ),
                "customer_email": (
                    customer_email
                ),
                "paid_at": (
                    paid_at.isoformat()
                ),
            }
        )

        report["payment"] = payment

        db_report.is_paid = True
        db_report.payment_status = "paid"

        db_report.stripe_session_id = (
            session_id
        )

        db_report.stripe_payment_intent_id = (
            payment_intent_id
        )

        db_report.customer_email = (
            customer_email
        )

        db_report.paid_at = paid_at

        db_report.report_json = (
            _json_dumps(
                report
            )
        )

        db_report.updated_at = (
            paid_at
        )

        db.commit()

        return True

    except SQLAlchemyError:
        db.rollback()
        return False

    finally:
        db.close()


def is_report_paid(
    report: dict,
) -> bool:
    """
    Return True only when the stored report
    has been marked paid.
    """

    return (
        (report.get("payment") or {})
        .get("status")
        == "paid"
    )