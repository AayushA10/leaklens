PLAN_CONFIG = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "max_sites": 1,
        "manual_scans_per_month": 3,
        "ai_analyses_per_month": 2,
        "scan_frequency": "weekly",
        "history_days": 7,
    },
    "starter": {
        "name": "Starter",
        "price_monthly": 5,
        "max_sites": 3,
        "manual_scans_per_month": 20,
        "ai_analyses_per_month": 10,
        "scan_frequency": "daily",
        "history_days": 30,
    },
    "growth": {
        "name": "Growth",
        "price_monthly": 15,
        "max_sites": 10,
        "manual_scans_per_month": 100,
        "ai_analyses_per_month": 50,
        "scan_frequency": "daily",
        "history_days": 90,
    },
    "pro": {
        "name": "Pro",
        "price_monthly": 29,
        "max_sites": 25,
        "manual_scans_per_month": 300,
        "ai_analyses_per_month": 150,
        "scan_frequency": "daily",
        "history_days": 365,
    },
}


def get_plan_config(plan: str) -> dict:
    return PLAN_CONFIG.get(plan, PLAN_CONFIG["free"])


from datetime import datetime, timedelta, timezone

from database.db import SessionLocal
from database.models import MonthlyUsage, MonitoredSite, UserSubscription


def get_or_create_subscription(user_id: str) -> UserSubscription:
    db = SessionLocal()

    try:
        subscription = (
            db.query(UserSubscription)
            .filter(UserSubscription.user_id == user_id)
            .first()
        )

        if subscription is None:
            subscription = UserSubscription(
                user_id=user_id,
                plan="free",
                status="active",
            )

            db.add(subscription)
            db.commit()
            db.refresh(subscription)

        return subscription

    finally:
        db.close()


def get_or_create_monthly_usage(user_id: str) -> MonthlyUsage:
    db = SessionLocal()

    try:
        billing_month = datetime.now(timezone.utc).strftime("%Y-%m")
        usage_id = f"{user_id}:{billing_month}"

        usage = (
            db.query(MonthlyUsage)
            .filter(MonthlyUsage.usage_id == usage_id)
            .first()
        )

        if usage is None:
            usage = MonthlyUsage(
                usage_id=usage_id,
                user_id=user_id,
                billing_month=billing_month,
                manual_scans=0,
                ai_analyses=0,
            )

            db.add(usage)
            db.commit()
            db.refresh(usage)

        return usage

    finally:
        db.close()


def get_user_plan_summary(user_id: str) -> dict:
    subscription = get_or_create_subscription(user_id)
    usage = get_or_create_monthly_usage(user_id)
    config = get_plan_config(subscription.plan)

    return {
        "plan": subscription.plan,
        "status": subscription.status,
        "name": config["name"],
        "price_monthly": config["price_monthly"],
        "limits": {
            "max_sites": config["max_sites"],
            "manual_scans_per_month": config[
                "manual_scans_per_month"
            ],
            "ai_analyses_per_month": config[
                "ai_analyses_per_month"
            ],
            "scan_frequency": config["scan_frequency"],
            "history_days": config["history_days"],
        },
        "usage": {
            "manual_scans": usage.manual_scans,
            "ai_analyses": usage.ai_analyses,
        },
    }


def can_add_monitored_site(user_id: str) -> dict:
    subscription = get_or_create_subscription(user_id)
    config = get_plan_config(subscription.plan)

    db = SessionLocal()

    try:
        from database.models import MonitoredSite

        current_sites = (
            db.query(MonitoredSite)
            .filter(MonitoredSite.owner_id == user_id)
            .count()
        )

        allowed = current_sites < config["max_sites"]

        return {
            "allowed": allowed,
            "plan": subscription.plan,
            "current_sites": current_sites,
            "max_sites": config["max_sites"],
            "scan_frequency": config["scan_frequency"],
        }

    finally:
        db.close()


def get_monitoring_frequency(user_id: str) -> str:
    subscription = get_or_create_subscription(user_id)
    config = get_plan_config(subscription.plan)

    return config["scan_frequency"]


def can_run_manual_scan(user_id: str) -> dict:
    subscription = get_or_create_subscription(user_id)
    usage = get_or_create_monthly_usage(user_id)
    config = get_plan_config(subscription.plan)

    limit = config["manual_scans_per_month"]
    used = usage.manual_scans

    return {
        "allowed": used < limit,
        "plan": subscription.plan,
        "used": used,
        "limit": limit,
        "remaining": max(limit - used, 0),
    }


def record_manual_scan(user_id: str) -> int:
    billing_month = datetime.now(timezone.utc).strftime("%Y-%m")
    usage_id = f"{user_id}:{billing_month}"

    # Ensure the row exists first.
    get_or_create_monthly_usage(user_id)

    db = SessionLocal()

    try:
        usage = (
            db.query(MonthlyUsage)
            .filter(MonthlyUsage.usage_id == usage_id)
            .first()
        )

        usage.manual_scans += 1

        db.commit()
        db.refresh(usage)

        return usage.manual_scans

    finally:
        db.close()



def can_run_ai_analysis(user_id: str) -> dict:
    subscription = get_or_create_subscription(user_id)
    usage = get_or_create_monthly_usage(user_id)
    config = get_plan_config(subscription.plan)

    limit = config["ai_analyses_per_month"]
    used = usage.ai_analyses

    return {
        "allowed": used < limit,
        "plan": subscription.plan,
        "used": used,
        "limit": limit,
        "remaining": max(limit - used, 0),
    }


def record_ai_analysis(user_id: str) -> int:
    billing_month = datetime.now(timezone.utc).strftime("%Y-%m")
    usage_id = f"{user_id}:{billing_month}"

    # Ensure the row exists first.
    get_or_create_monthly_usage(user_id)

    db = SessionLocal()

    try:
        usage = (
            db.query(MonthlyUsage)
            .filter(MonthlyUsage.usage_id == usage_id)
            .first()
        )

        usage.ai_analyses += 1

        db.commit()
        db.refresh(usage)

        return usage.ai_analyses

    finally:
        db.close()

def activate_subscription(
    user_id: str,
    plan: str,
    stripe_customer_id: str | None,
    stripe_subscription_id: str | None,
) -> dict:
    """
    Activate or update a paid LeakLens subscription
    after Stripe confirms Checkout completion.
    """

    normalized_plan = plan.strip().lower()

    if normalized_plan not in {
        "starter",
        "growth",
        "pro",
    }:
        raise ValueError(
            "Invalid paid subscription plan."
        )

    # Ensure every user has a subscription row.
    get_or_create_subscription(user_id)

    db = SessionLocal()

    try:
        subscription = (
            db.query(UserSubscription)
            .filter(
                UserSubscription.user_id == user_id
            )
            .first()
        )

        if subscription is None:
            raise RuntimeError(
                "User subscription record could not be found."
            )

        subscription.plan = normalized_plan
        subscription.status = "active"
        subscription.stripe_customer_id = (
            stripe_customer_id
        )
        subscription.stripe_subscription_id = (
            stripe_subscription_id
        )

        now = datetime.now(timezone.utc)
        sites = (
            db.query(MonitoredSite)
            .filter(MonitoredSite.owner_id == user_id)
            .all()
        )

        for site in sites:
            site.scan_frequency = "daily"
            site.next_scan_at = now + timedelta(days=1)

        db.commit()
        db.refresh(subscription)

        return {
            "user_id": subscription.user_id,
            "plan": subscription.plan,
            "status": subscription.status,
            "stripe_customer_id": (
                subscription.stripe_customer_id
            ),
            "stripe_subscription_id": (
                subscription.stripe_subscription_id
            ),
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def deactivate_subscription(
    stripe_subscription_id: str,
    status: str = "canceled",
) -> dict | None:
    """
    Deactivate a paid LeakLens subscription and
    return the user to the Free plan.
    """

    db = SessionLocal()

    try:
        subscription = (
            db.query(UserSubscription)
            .filter(
                UserSubscription.stripe_subscription_id
                == stripe_subscription_id
            )
            .first()
        )

        if subscription is None:
            return None

        subscription.plan = "free"
        subscription.status = status

        now = datetime.now(timezone.utc)
        sites = (
            db.query(MonitoredSite)
            .filter(
                MonitoredSite.owner_id == subscription.user_id
            )
            .all()
        )

        for site in sites:
            site.scan_frequency = "weekly"
            site.next_scan_at = now + timedelta(days=7)

        db.commit()
        db.refresh(subscription)

        return {
            "user_id": subscription.user_id,
            "plan": subscription.plan,
            "status": subscription.status,
            "stripe_customer_id": (
                subscription.stripe_customer_id
            ),
            "stripe_subscription_id": (
                subscription.stripe_subscription_id
            ),
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
