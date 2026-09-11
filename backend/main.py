from pathlib import Path
import os
import asyncio

from dotenv import load_dotenv

load_dotenv()

from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from scanner.crawler import scan_website
from scanner.seo import analyze_seo
from scanner.conversion import analyze_conversion
from scanner.performance import analyze_performance
from scanner.scoring import calculate_revenue_leak_score

from services.report_store import (
    get_report,
    is_report_paid,
    mark_report_paid,
    save_ai_analysis,
    save_checkout_session,
    save_report,
)

from services.groq_service import generate_ai_analysis

from services.pdf_service import (
    generate_pdf_report,
    get_pdf_path,
)

from services.stripe_service import (
    construct_webhook_event,
    create_checkout_session,
    verify_paid_session,
)

from database.db import init_db


init_db()


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Revenue Leak Scanner API",
    description=(
        "Backend API for scanning websites and identifying "
        "potential revenue leaks."
    ),
    version="2.0.1",
)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)


# =================================
# CORS
# =================================

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =================================
# HELPERS
# =================================

def _build_free_response(
    report_id: str,
    report: dict,
) -> dict:
    website_data = report.get(
        "website",
        {},
    )

    performance_result = report.get(
        "performance",
        {},
    )

    revenue_leak_result = report.get(
        "revenue_leak",
        {},
    )

    payment = report.get(
        "payment"
    ) or {}

    return {
        "success": True,
        "report_id": report_id,
        "website": {
            "url": website_data.get(
                "url"
            ),
            "final_url": website_data.get(
                "final_url"
            ),
            "title": website_data.get(
                "title"
            ),
        },
        "performance": {
            "status": performance_result.get(
                "status"
            ),
            "load_time_ms": performance_result.get(
                "load_time_ms"
            ),
            "requests_count": performance_result.get(
                "requests_count"
            ),
        },
        "revenue_leak": {
            "health_score": revenue_leak_result.get(
                "health_score"
            ),
            "leak_score": revenue_leak_result.get(
                "leak_score"
            ),
            "risk_level": revenue_leak_result.get(
                "risk_level"
            ),
            "category_scores": revenue_leak_result.get(
                "category_scores"
            ),
            "total_issues": revenue_leak_result.get(
                "total_issues"
            ),
            "critical_issues": revenue_leak_result.get(
                "critical_issues"
            ),
            "high_issues": revenue_leak_result.get(
                "high_issues"
            ),
            "top_issues": (
                revenue_leak_result.get(
                    "top_issues",
                    [],
                )[:3]
            ),
        },
        "payment": {
            "status": payment.get(
                "status",
                "unpaid",
            ),
            "price_usd": 29,
        },
    }


def _require_paid_report(
    report_id: str,
) -> dict:
    report = get_report(
        report_id
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found or expired.",
        )

    if not is_report_paid(
        report
    ):
        raise HTTPException(
            status_code=402,
            detail=(
                "Payment is required to access "
                "the full report."
            ),
        )

    return report


def _stripe_object_to_dict(
    obj,
) -> dict:
    """
    Convert Stripe SDK objects to normal dictionaries safely.

    Stripe objects are not guaranteed to support dict.get()
    directly in every SDK version, so normalizing them here
    avoids compatibility issues.
    """

    if obj is None:
        return {}

    if isinstance(
        obj,
        dict,
    ):
        return obj

    to_dict_recursive = getattr(
        obj,
        "to_dict_recursive",
        None,
    )

    if callable(
        to_dict_recursive
    ):
        try:
            return to_dict_recursive()
        except Exception:
            pass

    to_dict = getattr(
        obj,
        "to_dict",
        None,
    )

    if callable(
        to_dict
    ):
        try:
            return to_dict()
        except Exception:
            pass

    try:
        return dict(
            obj
        )
    except Exception:
        return {}


# =================================
# ROOT
# =================================

@app.get("/")
def root():
    return {
        "message": "Revenue Leak Scanner API is running",
        "status": "ok",
    }


# =================================
# HEALTH CHECK
# =================================

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }


# =================================
# WEBSITE SCAN
# =================================

@app.get("/scan")
@limiter.limit("10/minute")
async def scan(
    request: Request,
    url: str = Query(
        ...,
        description="Website URL to scan",
    ),
):
    website_data, performance_result = await asyncio.gather(
        scan_website(url),
        analyze_performance(url),
    )

    if not website_data.get(
        "success"
    ):
        return {
            "success": False,
            "error": website_data.get(
                "error",
                "Unable to scan website.",
            ),
        }

    seo_result = analyze_seo(
        website_data
    )

    conversion_result = analyze_conversion(
        website_data
    )


    revenue_leak_result = (
        calculate_revenue_leak_score(
            seo_result,
            conversion_result,
            performance_result,
        )
    )

    full_report = {
        "website": website_data,
        "seo": seo_result,
        "conversion": conversion_result,
        "performance": performance_result,
        "revenue_leak": revenue_leak_result,
        "ai_analysis": None,
        "payment": {
            "status": "unpaid",
            "price_usd": 29,
        },
    }

    report_id = save_report(
        full_report
    )

    return _build_free_response(
        report_id,
        full_report,
    )


# =================================
# FREE PREVIEW RESTORE
# =================================

@app.get(
    "/report/{report_id}/preview"
)
def get_report_preview(
    report_id: str,
):
    report = get_report(
        report_id
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found or expired.",
        )

    return _build_free_response(
        report_id,
        report,
    )


# =================================
# PAYMENT STATUS
# =================================

@app.get(
    "/report/{report_id}/payment-status"
)
def get_payment_status(
    report_id: str,
):
    report = get_report(
        report_id
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found or expired.",
        )

    payment = report.get(
        "payment"
    ) or {}

    return {
        "success": True,
        "report_id": report_id,
        "paid": is_report_paid(
            report
        ),
        "status": payment.get(
            "status",
            "unpaid",
        ),
    }


# =================================
# CREATE STRIPE CHECKOUT
# =================================

@app.post(
    "/report/{report_id}/checkout"
)
def create_report_checkout(
    report_id: str,
):
    report = get_report(
        report_id
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found or expired.",
        )

    if is_report_paid(
        report
    ):
        return {
            "success": True,
            "already_paid": True,
            "report_id": report_id,
        }

    try:
        session = create_checkout_session(
            report_id
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Unable to create Stripe checkout: "
                f"{str(exc)}"
            ),
        )

    saved = save_checkout_session(
        report_id,
        session.id,
    )

    if not saved:
        raise HTTPException(
            status_code=500,
            detail=(
                "Stripe checkout was created, but the "
                "session could not be saved."
            ),
        )

    return {
        "success": True,
        "already_paid": False,
        "report_id": report_id,
        "checkout_url": session.url,
        "session_id": session.id,
    }


# =================================
# CONFIRM STRIPE RETURN
# =================================

@app.post(
    "/payments/confirm"
)
def confirm_payment(
    session_id: str = Query(
        ...,
        description="Stripe Checkout Session ID",
    )
):
    try:
        payment_result = verify_paid_session(
            session_id
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(
                exc
            ),
        )

    if not payment_result.get(
        "paid"
    ):
        raise HTTPException(
            status_code=402,
            detail=(
                "Stripe has not marked this "
                "Checkout Session as paid."
            ),
        )

    report_id = payment_result.get(
        "report_id"
    )

    if not report_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Confirmed Stripe payment does not "
                "contain a report ID."
            ),
        )

    report = get_report(
        report_id
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found or expired.",
        )

    saved = mark_report_paid(
        report_id=report_id,
        session_id=payment_result.get(
            "session_id"
        ),
        payment_intent_id=payment_result.get(
            "payment_intent_id"
        ),
        customer_email=payment_result.get(
            "customer_email"
        ),
    )

    if not saved:
        raise HTTPException(
            status_code=500,
            detail=(
                "Payment was confirmed but the "
                "report could not be unlocked."
            ),
        )

    return {
        "success": True,
        "paid": True,
        "report_id": report_id,
    }


# =================================
# STRIPE WEBHOOK
# =================================

@app.post(
    "/stripe/webhook"
)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(
        default="",
        alias="Stripe-Signature",
    ),
):
    payload = await request.body()

    if not stripe_signature:
        raise HTTPException(
            status_code=400,
            detail=(
                "Missing Stripe-Signature header."
            ),
        )

    try:
        event = construct_webhook_event(
            payload,
            stripe_signature,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid Stripe webhook: "
                f"{str(exc)}"
            ),
        )

    event_data = _stripe_object_to_dict(
        event
    )

    event_type = event_data.get(
        "type"
    )

    if event_type in {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    }:
        data = event_data.get(
            "data"
        ) or {}

        session = data.get(
            "object"
        )

        session_data = _stripe_object_to_dict(
            session
        )

        metadata = session_data.get(
            "metadata"
        ) or {}

        if not isinstance(
            metadata,
            dict,
        ):
            metadata = (
                _stripe_object_to_dict(
                    metadata
                )
            )

        report_id = (
            metadata.get(
                "report_id"
            )
            or session_data.get(
                "client_reference_id"
            )
        )

        payment_status = session_data.get(
            "payment_status"
        )

        if (
            report_id
            and payment_status == "paid"
        ):
            customer_details = session_data.get(
                "customer_details"
            ) or {}

            if not isinstance(
                customer_details,
                dict,
            ):
                customer_details = (
                    _stripe_object_to_dict(
                        customer_details
                    )
                )

            mark_report_paid(
                report_id=report_id,
                session_id=session_data.get(
                    "id"
                ),
                payment_intent_id=session_data.get(
                    "payment_intent"
                ),
                customer_email=customer_details.get(
                    "email"
                ),
            )

    return {
        "received": True,
    }


# =================================
# FULL REPORT - PAID ONLY
# =================================

@app.get(
    "/report/{report_id}"
)
def get_full_report(
    report_id: str,
):
    report = _require_paid_report(
        report_id
    )

    return {
        "success": True,
        "report_id": report_id,
        "report": report,
    }


# =================================
# GROQ AI - PAID ONLY
# =================================

@app.post(
    "/report/{report_id}/generate-ai"
)
async def generate_report_ai_analysis(
    report_id: str,
):
    report = _require_paid_report(
        report_id
    )

    existing_analysis = report.get(
        "ai_analysis"
    )

    if existing_analysis:
        return {
            "success": True,
            "report_id": report_id,
            "cached": True,
            "analysis": existing_analysis,
        }

    ai_result = await generate_ai_analysis(
        report
    )

    if not ai_result.get(
        "success"
    ):
        raise HTTPException(
            status_code=502,
            detail=ai_result.get(
                "error",
                "Unable to generate AI analysis.",
            ),
        )

    analysis = ai_result.get(
        "analysis"
    )

    saved = save_ai_analysis(
        report_id,
        analysis,
    )

    if not saved:
        raise HTTPException(
            status_code=500,
            detail=(
                "AI analysis was generated but "
                "could not be saved."
            ),
        )

    return {
        "success": True,
        "report_id": report_id,
        "cached": False,
        "analysis": analysis,
    }


# =================================
# PDF - PAID ONLY
# =================================

@app.get(
    "/report/{report_id}/pdf"
)
async def download_pdf_report(
    report_id: str,
):
    report = _require_paid_report(
        report_id
    )

    existing_pdf = get_pdf_path(
        report_id
    )

    if existing_pdf:
        pdf_path = Path(
            existing_pdf
        )

        if pdf_path.exists():
            return FileResponse(
                path=str(
                    pdf_path
                ),
                media_type="application/pdf",
                filename=(
                    f"LeakLens-Report-"
                    f"{report_id}.pdf"
                ),
            )

    if not report.get(
        "ai_analysis"
    ):
        ai_result = await generate_ai_analysis(
            report
        )

        if not ai_result.get(
            "success"
        ):
            raise HTTPException(
                status_code=502,
                detail=ai_result.get(
                    "error",
                    (
                        "Unable to generate AI "
                        "analysis for the PDF."
                    ),
                ),
            )

        analysis = ai_result.get(
            "analysis"
        )

        saved = save_ai_analysis(
            report_id,
            analysis,
        )

        if not saved:
            raise HTTPException(
                status_code=500,
                detail=(
                    "AI analysis was generated "
                    "but could not be saved."
                ),
            )

        report = get_report(
            report_id
        )

        if not report:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Report could not be reloaded "
                    "after AI generation."
                ),
            )

    try:
        pdf_file = generate_pdf_report(
            report_id,
            report,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to generate PDF report: "
                f"{str(exc)}"
            ),
        )

    pdf_path = Path(
        pdf_file
    )

    if not pdf_path.exists():
        raise HTTPException(
            status_code=500,
            detail=(
                "PDF generation completed but "
                "the file could not be found."
            ),
        )

    return FileResponse(
        path=str(
            pdf_path
        ),
        media_type="application/pdf",
        filename=(
            f"LeakLens-Report-"
            f"{report_id}.pdf"
        ),
    )