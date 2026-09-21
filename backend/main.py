from pathlib import Path
import os
import asyncio

from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.local", override=True)

from fastapi import (
    Body,
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from clerk_backend_api import (
    AuthenticateRequestOptions,
    authenticate_request,
)
from clerk_backend_api.security.types import AuthStatus

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from scanner.crawler import scan_website
from scanner.seo import analyze_seo
from scanner.conversion import analyze_conversion
from scanner.performance import analyze_performance_raw
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
    create_customer_portal_session,
    create_subscription_checkout_session,
    get_plan_from_price_id,
    verify_paid_session,
)

from services.monitoring_service import (
    create_monitored_site,
    get_owned_monitored_site,
    get_latest_snapshot,
    snapshot_report,
    list_monitored_sites,
    list_scan_snapshots,
    list_site_issues,
    run_due_monitoring_scans,
    run_monitoring_scan,
    set_monitoring_enabled,
)

from services.plan_service import (
    activate_subscription,
    can_add_monitored_site,
    can_run_ai_analysis,
    can_run_manual_scan,
    deactivate_subscription,
    record_ai_analysis,
    record_manual_scan,
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

def _require_clerk_user(request: Request) -> str:
    secret_key = os.getenv("CLERK_SECRET_KEY")
    if not secret_key:
        raise HTTPException(
            status_code=500,
            detail="Authentication is not configured.",
        )

    try:
        auth_state = authenticate_request(
            request,
            AuthenticateRequestOptions(
                secret_key=secret_key,
            ),
        )
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token.",
        )

    if auth_state.status != AuthStatus.SIGNED_IN:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    payload = auth_state.payload or {}
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authenticated user ID missing.",
        )

    return str(user_id)


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
    website_data = await scan_website(
        url
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

    performance_result = analyze_performance_raw(
        website_data.get("performance_raw")
    )

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
# CREATE SUBSCRIPTION CHECKOUT
# =================================

@app.post("/account/subscription/checkout")
def create_subscription_checkout(
    request: Request,
    plan: str = Query(...),
):
    owner_id = _require_clerk_user(request)

    normalized_plan = plan.strip().lower()

    if normalized_plan not in {
        "starter",
        "growth",
        "pro",
    }:
        raise HTTPException(
            status_code=400,
            detail="Invalid subscription plan.",
        )

    from services.plan_service import get_or_create_subscription

    existing_subscription = get_or_create_subscription(
        owner_id
    )

    if (
        existing_subscription.plan in {
            "starter",
            "growth",
            "pro",
        }
        and existing_subscription.status == "active"
        and existing_subscription.stripe_subscription_id
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "You already have an active subscription. "
                "Manage your existing plan instead of "
                "creating another subscription."
            ),
        )

    try:
        session = create_subscription_checkout_session(
            user_id=owner_id,
            plan=normalized_plan,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Unable to create subscription checkout: "
                f"{str(exc)}"
            ),
        )

    return {
        "success": True,
        "plan": normalized_plan,
        "checkout_url": session.url,
        "session_id": session.id,
    }


# =================================
# MANAGE SUBSCRIPTION
# =================================

@app.post("/account/subscription/manage")
def manage_subscription(
    request: Request,
):
    owner_id = _require_clerk_user(request)

    from services.plan_service import get_or_create_subscription

    subscription = get_or_create_subscription(
        owner_id
    )

    if not subscription.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "No Stripe billing account exists "
                "for this user."
            ),
        )

    try:
        session = create_customer_portal_session(
            subscription.stripe_customer_id,
            subscription.stripe_subscription_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Unable to open subscription management: "
                f"{str(exc)}"
            ),
        )

    return {
        "success": True,
        "portal_url": session.url,
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

        product = metadata.get(
            "product"
        )

        if product == "leaklens_subscription":
            user_id = metadata.get(
                "user_id"
            ) or session_data.get(
                "client_reference_id"
            )

            plan = metadata.get(
                "plan"
            )

            subscription_id = session_data.get(
                "subscription"
            )

            customer_id = session_data.get(
                "customer"
            )

            if (
                user_id
                and plan
                and subscription_id
            ):
                activate_subscription(
                    user_id=user_id,
                    plan=plan,
                    stripe_customer_id=customer_id,
                    stripe_subscription_id=subscription_id,
                )

            return {
                "received": True,
            }

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

    if event_type in {
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        data = event_data.get(
            "data"
        ) or {}

        stripe_subscription = _stripe_object_to_dict(
            data.get(
                "object"
            )
        )

        subscription_id = stripe_subscription.get(
            "id"
        )

        stripe_status = stripe_subscription.get(
            "status"
        )

        if subscription_id:
            if (
                event_type
                == "customer.subscription.deleted"
            ):
                deactivate_subscription(
                    stripe_subscription_id=subscription_id,
                    status="canceled",
                )

            elif stripe_status in {
                "past_due",
                "unpaid",
                "canceled",
                "incomplete_expired",
            }:
                deactivate_subscription(
                    stripe_subscription_id=subscription_id,
                    status=stripe_status,
                )

            elif stripe_status in {
                "active",
                "trialing",
            }:
                items = _stripe_object_to_dict(
                    stripe_subscription.get("items")
                )
                item_list = items.get("data") or []

                if item_list:
                    first_item = _stripe_object_to_dict(
                        item_list[0]
                    )
                    price = _stripe_object_to_dict(
                        first_item.get("price")
                    )
                    price_id = price.get("id")
                    plan = get_plan_from_price_id(
                        price_id
                    )

                    metadata = _stripe_object_to_dict(
                        stripe_subscription.get(
                            "metadata"
                        )
                    )

                    user_id = metadata.get(
                        "user_id"
                    )

                    customer_id = (
                        stripe_subscription.get(
                            "customer"
                        )
                    )

                    if user_id and plan:
                        activate_subscription(
                            user_id=user_id,
                            plan=plan,
                            stripe_customer_id=customer_id,
                            stripe_subscription_id=subscription_id,
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


# =================================
# MONITORING
# =================================

@app.post("/monitoring/sites")
def add_monitored_site(
    request: Request,
    website_url: str = Body(..., embed=True),
    website_title: str | None = Body(
        None,
        embed=True,
    ),
):
    owner_id = _require_clerk_user(
        request
    )

    website_url = website_url.strip()

    if not website_url:
        raise HTTPException(
            status_code=400,
            detail="Website URL is required.",
        )

    plan_access = can_add_monitored_site(owner_id)

    if not plan_access["allowed"]:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "SITE_LIMIT_REACHED",
                "message": (
                    f"{plan_access['plan'].title()} plan allows "
                    f"up to {plan_access['max_sites']} monitored site(s). "
                    "Upgrade your plan to monitor more websites."
                ),
                "plan": plan_access["plan"],
                "current_sites": plan_access["current_sites"],
                "max_sites": plan_access["max_sites"],
            },
        )

    site = create_monitored_site(
        website_url=website_url,
        owner_id=owner_id,
        website_title=website_title,
        scan_frequency=plan_access["scan_frequency"],
    )

    return {
        "success": True,
        "site": {
            "site_id": site.site_id,
            "website_url": site.website_url,
            "website_title": site.website_title,
            "monitoring_enabled": (
                site.monitoring_enabled
            ),
            "scan_frequency": (
                site.scan_frequency
            ),
            "last_scanned_at": (
                site.last_scanned_at
            ),
            "next_scan_at": (
                site.next_scan_at
            ),
            "created_at": site.created_at,
        },
    }


@app.get("/monitoring/sites")
def get_monitoring_sites(
    request: Request,
):
    owner_id = _require_clerk_user(
        request
    )

    sites = list_monitored_sites(
        owner_id
    )

    return {
        "success": True,
        "sites": [
            {
                "site_id": site.site_id,
                "website_url": site.website_url,
                "website_title": site.website_title,
                "monitoring_enabled": (
                    site.monitoring_enabled
                ),
                "scan_frequency": (
                    site.scan_frequency
                ),
                "last_scanned_at": (
                    site.last_scanned_at
                ),
                "next_scan_at": (
                    site.next_scan_at
                ),
                "created_at": site.created_at,
                "updated_at": site.updated_at,
            }
            for site in sites
        ],
    }


@app.get("/monitoring/sites/{site_id}")
def get_monitoring_site(
    site_id: str,
    request: Request,
):
    owner_id = _require_clerk_user(
        request
    )

    site = get_owned_monitored_site(
        site_id=site_id,
        owner_id=owner_id,
    )

    if site is None:
        raise HTTPException(
            status_code=404,
            detail="Monitored site not found.",
        )

    return {
        "success": True,
        "site": {
            "site_id": site.site_id,
            "website_url": site.website_url,
            "website_title": site.website_title,
            "monitoring_enabled": (
                site.monitoring_enabled
            ),
            "scan_frequency": (
                site.scan_frequency
            ),
            "last_scanned_at": (
                site.last_scanned_at
            ),
            "next_scan_at": (
                site.next_scan_at
            ),
            "created_at": site.created_at,
            "updated_at": site.updated_at,
        },
    }


@app.post("/monitoring/sites/{site_id}/scan")
async def scan_monitored_site(
    site_id: str,
    request: Request,
):
    owner_id = _require_clerk_user(
        request
    )

    site = get_owned_monitored_site(
        site_id=site_id,
        owner_id=owner_id,
    )

    if site is None:
        raise HTTPException(
            status_code=404,
            detail="Monitored site not found.",
        )

    scan_access = can_run_manual_scan(owner_id)

    if not scan_access["allowed"]:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "MANUAL_SCAN_LIMIT_REACHED",
                "message": (
                    f"{scan_access['plan'].title()} plan allows "
                    f"{scan_access['limit']} manual scans per month. "
                    "Upgrade your plan for more scans."
                ),
                "plan": scan_access["plan"],
                "used": scan_access["used"],
                "limit": scan_access["limit"],
                "remaining": scan_access["remaining"],
            },
        )

    try:
        result = await run_monitoring_scan(
            site_id
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Monitoring scan failed: "
                f"{str(exc)}"
            ),
        )

    if not result.get("success"):
        raise HTTPException(
            status_code=502,
            detail=result.get(
                "error",
                "Monitoring scan failed.",
            ),
        )

    record_manual_scan(owner_id)

    return result


@app.post("/monitoring/sites/{site_id}/toggle")
def toggle_site_monitoring(
    site_id: str,
    request: Request,
):
    owner_id = _require_clerk_user(
        request
    )

    site = get_owned_monitored_site(
        site_id=site_id,
        owner_id=owner_id,
    )

    if site is None:
        raise HTTPException(
            status_code=404,
            detail="Monitored site not found.",
        )

    updated_site = set_monitoring_enabled(
        site_id=site_id,
        enabled=not site.monitoring_enabled,
    )

    if updated_site is None:
        raise HTTPException(
            status_code=404,
            detail="Monitored site not found.",
        )

    return {
        "success": True,
        "monitoring_enabled": (
            updated_site.monitoring_enabled
        ),
        "next_scan_at": (
            updated_site.next_scan_at
        ),
    }


@app.get("/monitoring/sites/{site_id}/history")
def get_monitoring_history(
    site_id: str,
    request: Request,
    limit: int = Query(
        30,
        ge=1,
        le=100,
    ),
):
    owner_id = _require_clerk_user(
        request
    )

    site = get_owned_monitored_site(
        site_id=site_id,
        owner_id=owner_id,
    )

    if site is None:
        raise HTTPException(
            status_code=404,
            detail="Monitored site not found.",
        )

    snapshots = list_scan_snapshots(
        site_id=site_id,
        limit=limit,
    )

    return {
        "success": True,
        "site_id": site_id,
        "history": [
            {
                "snapshot_id": (
                    snapshot.snapshot_id
                ),
                "success": snapshot.success,
                "created_at": (
                    snapshot.created_at
                ),
            }
            for snapshot in snapshots
        ],
    }


@app.get("/monitoring/sites/{site_id}/issues")
def get_monitoring_issues(
    site_id: str,
    request: Request,
    status: str | None = Query(
        None,
    ),
):
    owner_id = _require_clerk_user(
        request
    )

    site = get_owned_monitored_site(
        site_id=site_id,
        owner_id=owner_id,
    )

    if site is None:
        raise HTTPException(
            status_code=404,
            detail="Monitored site not found.",
        )

    if status not in (
        None,
        "open",
        "resolved",
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Status must be open or resolved."
            ),
        )

    issues = list_site_issues(
        site_id=site_id,
        status=status,
    )

    return {
        "success": True,
        "site_id": site_id,
        "issues": [
            {
                "issue_id": issue.issue_id,
                "fingerprint": issue.fingerprint,
                "category": issue.category,
                "issue_type": issue.issue_type,
                "severity": issue.severity,
                "message": issue.message,
                "recommendation": (
                    issue.recommendation
                ),
                "status": issue.status,
                "first_seen_at": (
                    issue.first_seen_at
                ),
                "last_seen_at": (
                    issue.last_seen_at
                ),
                "resolved_at": (
                    issue.resolved_at
                ),
            }
            for issue in issues
        ],
    }


@app.post("/internal/run-monitoring")
async def run_scheduled_monitoring(
    x_cron_secret: str | None = Header(default=None),
):
    expected_secret = os.getenv("CRON_SECRET")

    if not expected_secret:
        raise HTTPException(
            status_code=500,
            detail="Cron authentication is not configured.",
        )

    if x_cron_secret != expected_secret:
        raise HTTPException(
            status_code=401,
            detail="Invalid cron credentials.",
        )

    return await run_due_monitoring_scans()


# =================================
# SUBSCRIPTION / PLAN
# =================================

# =================================
# MONITORED SITE AI ANALYSIS
# =================================

@app.post("/monitoring/sites/{site_id}/ai-analysis")
async def generate_monitoring_ai_analysis(
    site_id: str,
    request: Request,
):
    owner_id = _require_clerk_user(request)

    site = get_owned_monitored_site(
        site_id=site_id,
        owner_id=owner_id,
    )

    if site is None:
        raise HTTPException(
            status_code=404,
            detail="Monitored site not found.",
        )

    snapshot = get_latest_snapshot(
        site_id
    )

    report = snapshot_report(
        snapshot
    )

    if not report:
        raise HTTPException(
            status_code=409,
            detail=(
                "No completed scan is available for "
                "AI analysis. Run a scan first."
            ),
        )

    ai_access = can_run_ai_analysis(
        owner_id
    )

    if not ai_access["allowed"]:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "AI_ANALYSIS_LIMIT_REACHED",
                "message": (
                    "Monthly AI analysis limit reached "
                    "for your current plan."
                ),
                "plan": ai_access["plan"],
                "used": ai_access["used"],
                "limit": ai_access["limit"],
                "remaining": ai_access["remaining"],
            },
        )

    ai_result = await generate_ai_analysis(
        report
    )

    if not ai_result.get("success"):
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

    if not analysis:
        raise HTTPException(
            status_code=502,
            detail="AI analysis returned no usable result.",
        )

    used = record_ai_analysis(
        owner_id
    )

    return {
        "success": True,
        "site_id": site_id,
        "snapshot_id": snapshot.snapshot_id,
        "analysis": analysis,
        "usage": {
            "used": used,
            "limit": ai_access["limit"],
            "remaining": max(
                ai_access["limit"] - used,
                0,
            ),
        },
    }


@app.get("/account/plan")
def get_account_plan(
    request: Request,
):
    owner_id = _require_clerk_user(request)

    from services.plan_service import get_user_plan_summary

    summary = get_user_plan_summary(owner_id)
    sites = list_monitored_sites(owner_id)

    summary["usage"]["monitored_sites"] = len(sites)
    summary["usage"]["sites_remaining"] = max(
        summary["limits"]["max_sites"] - len(sites),
        0,
    )

    return {
        "success": True,
        **summary,
    }
