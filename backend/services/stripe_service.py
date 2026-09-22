import os
from typing import Optional

import stripe


REPORT_PRICE_CENTS = 2900
REPORT_CURRENCY = "usd"
REPORT_PRODUCT_NAME = "LeakLens Full Revenue Leak Report"


# =================================
# HELPERS
# =================================

def _get_secret_key() -> str:
    secret_key = os.getenv(
        "STRIPE_SECRET_KEY"
    )

    if not secret_key:
        raise RuntimeError(
            "STRIPE_SECRET_KEY is not configured."
        )

    return secret_key


def _get_frontend_url() -> str:
    return (
        os.getenv(
            "FRONTEND_URL"
        )
        or "http://localhost:5173"
    ).rstrip("/")


def _configure_stripe():
    stripe.api_key = _get_secret_key()


def _stripe_to_dict(
    obj,
) -> dict:
    """
    Convert Stripe SDK objects into a normal Python dict.

    Newer Stripe SDK versions return StripeObject instances.
    Those should not be treated as regular dictionaries.
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
            result = to_dict_recursive()

            if isinstance(
                result,
                dict,
            ):
                return result

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
            result = to_dict()

            if isinstance(
                result,
                dict,
            ):
                return result

        except Exception:
            pass

    try:
        return dict(
            obj
        )

    except Exception as exc:
        raise RuntimeError(
            "Unable to convert Stripe object "
            "to a Python dictionary."
        ) from exc


# =================================
# CREATE CHECKOUT SESSION
# =================================

def create_checkout_session(
    report_id: str,
):
    """
    Create a Stripe-hosted one-time Checkout Session
    for a LeakLens full report.
    """

    _configure_stripe()

    frontend_url = _get_frontend_url()

    success_url = (
        f"{frontend_url}/"
        f"?payment=success"
        f"&report_id={report_id}"
        f"&session_id={{CHECKOUT_SESSION_ID}}"
    )

    cancel_url = (
        f"{frontend_url}/"
        f"?payment=cancelled"
        f"&report_id={report_id}"
    )

    session = stripe.checkout.Session.create(
        mode="payment",
        client_reference_id=report_id,
        metadata={
            "report_id": report_id,
            "product": "leaklens_full_report",
        },
        line_items=[
            {
                "price_data": {
                    "currency": REPORT_CURRENCY,
                    "unit_amount": REPORT_PRICE_CENTS,
                    "product_data": {
                        "name": REPORT_PRODUCT_NAME,
                        "description": (
                            "Full technical findings, "
                            "AI executive analysis, "
                            "prioritized fixes, "
                            "30-day plan, and "
                            "downloadable PDF."
                        ),
                    },
                },
                "quantity": 1,
            }
        ],
        success_url=success_url,
        cancel_url=cancel_url,
    )

    return session


# =================================
# RETRIEVE CHECKOUT SESSION
# =================================

def retrieve_checkout_session(
    session_id: str,
):
    """
    Retrieve a Checkout Session directly from Stripe.
    """

    _configure_stripe()

    return stripe.checkout.Session.retrieve(
        session_id
    )


# =================================
# VERIFY PAYMENT
# =================================

def verify_paid_session(
    session_id: str,
    expected_report_id: Optional[str] = None,
) -> dict:
    """
    Retrieve and verify a successful Stripe Checkout Session.
    """

    session = retrieve_checkout_session(
        session_id
    )

    session_data = _stripe_to_dict(
        session
    )

    metadata_raw = session_data.get(
        "metadata"
    )

    metadata = _stripe_to_dict(
        metadata_raw
    )

    report_id = (
        metadata.get(
            "report_id"
        )
        or session_data.get(
            "client_reference_id"
        )
    )

    if not report_id:
        raise RuntimeError(
            "Stripe session does not contain a report ID."
        )

    if (
        expected_report_id
        and report_id != expected_report_id
    ):
        raise RuntimeError(
            "Stripe session does not match this report."
        )

    payment_status = session_data.get(
        "payment_status"
    )

    payment_intent_id = session_data.get(
        "payment_intent"
    )

    customer_details_raw = session_data.get(
        "customer_details"
    )

    customer_details = _stripe_to_dict(
        customer_details_raw
    )

    customer_email = customer_details.get(
        "email"
    )

    if payment_status != "paid":
        return {
            "paid": False,
            "report_id": report_id,
            "session_id": session_data.get(
                "id"
            ),
            "payment_status": payment_status,
            "payment_intent_id": payment_intent_id,
            "customer_email": customer_email,
        }

    return {
        "paid": True,
        "report_id": report_id,
        "session_id": session_data.get(
            "id"
        ),
        "payment_status": payment_status,
        "payment_intent_id": payment_intent_id,
        "customer_email": customer_email,
    }


# =================================
# WEBHOOK
# =================================

def construct_webhook_event(
    payload: bytes,
    signature: str,
):
    """
    Verify and construct a Stripe webhook event.
    """

    webhook_secret = os.getenv(
        "STRIPE_WEBHOOK_SECRET"
    )

    if not webhook_secret:
        raise RuntimeError(
            "STRIPE_WEBHOOK_SECRET is not configured."
        )

    return stripe.Webhook.construct_event(
        payload=payload,
        sig_header=signature,
        secret=webhook_secret,
    )

# =================================
# SUBSCRIPTION CHECKOUT
# =================================

SUBSCRIPTION_PLANS = {
    "starter": {
        "price_env": "STRIPE_STARTER_PRICE_ID",
        "name": "LeakLens Starter",
    },
    "growth": {
        "price_env": "STRIPE_GROWTH_PRICE_ID",
        "name": "LeakLens Growth",
    },
    "pro": {
        "price_env": "STRIPE_PRO_PRICE_ID",
        "name": "LeakLens Pro",
    },
}


def create_subscription_checkout_session(
    user_id: str,
    plan: str,
):
    """
    Create a Stripe-hosted recurring monthly Checkout Session
    for a LeakLens SaaS subscription.
    """

    _configure_stripe()

    normalized_plan = plan.strip().lower()

    plan_config = SUBSCRIPTION_PLANS.get(
        normalized_plan
    )

    if not plan_config:
        raise ValueError(
            "Invalid subscription plan."
        )

    frontend_url = _get_frontend_url()

    success_url = (
        f"{frontend_url}/dashboard"
        f"?subscription=success"
        f"&session_id={{CHECKOUT_SESSION_ID}}"
    )

    cancel_url = (
        f"{frontend_url}/#pricing"
    )

    session = stripe.checkout.Session.create(
        mode="subscription",
        client_reference_id=user_id,
        metadata={
            "user_id": user_id,
            "plan": normalized_plan,
            "product": "leaklens_subscription",
        },
        subscription_data={
            "metadata": {
                "user_id": user_id,
                "plan": normalized_plan,
                "product": "leaklens_subscription",
            },
        },
        line_items=[
            {
                "price": price_id,
                "quantity": 1,
            }
        ],
        success_url=success_url,
        cancel_url=cancel_url,
    )

    return session


def create_customer_portal_session(
    stripe_customer_id: str,
    stripe_subscription_id: str | None = None,
):
    """
    Create a Stripe Billing Portal session.

    When a subscription ID is available, deep link
    directly into the plan update flow and return to
    the LeakLens dashboard after completion.
    """

    if not stripe_customer_id:
        raise ValueError(
            "Stripe customer ID is required."
        )

    _configure_stripe()

    frontend_url = _get_frontend_url()
    dashboard_url = f"{frontend_url}/dashboard"

    session_params = {
        "customer": stripe_customer_id,
        "return_url": dashboard_url,
    }

    if stripe_subscription_id:
        session_params["flow_data"] = {
            "type": "subscription_update",
            "subscription_update": {
                "subscription": stripe_subscription_id,
            },
            "after_completion": {
                "type": "redirect",
                "redirect": {
                    "return_url": dashboard_url,
                },
            },
        }

    session = stripe.billing_portal.Session.create(
        **session_params
    )

    return session


def get_plan_from_price_id(
    price_id: str | None,
) -> str | None:
    """
    Map a Stripe recurring Price ID back to a
    LeakLens subscription plan.
    """

    if not price_id:
        return None

    for plan, config in SUBSCRIPTION_PLANS.items():
        configured_price_id = os.getenv(
            config["price_env"]
        )

        if (
            configured_price_id
            and configured_price_id == price_id
        ):
            return plan

    return None
