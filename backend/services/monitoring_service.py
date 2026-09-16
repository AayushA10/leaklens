import json
import uuid
from datetime import datetime, timedelta, timezone

from database.db import SessionLocal
from database.models import LeakIssue, MonitoredSite, ScanSnapshot

from scanner.crawler import scan_website
from scanner.seo import analyze_seo
from scanner.conversion import analyze_conversion
from scanner.performance import analyze_performance_raw
from scanner.scoring import calculate_revenue_leak_score


def create_monitored_site(
    website_url: str,
    website_title: str | None = None,
) -> MonitoredSite:
    db = SessionLocal()

    try:
        now = datetime.now(timezone.utc)

        site = MonitoredSite(
            site_id=uuid.uuid4().hex,
            website_url=website_url,
            website_title=website_title,
            monitoring_enabled=True,
            scan_frequency="daily",
            next_scan_at=now,
        )

        db.add(site)
        db.commit()
        db.refresh(site)

        return site

    finally:
        db.close()


def create_scan_snapshot(
    site_id: str,
    report: dict,
    success: bool = True,
) -> ScanSnapshot:
    db = SessionLocal()

    try:
        snapshot = ScanSnapshot(
            snapshot_id=uuid.uuid4().hex,
            site_id=site_id,
            report_json=json.dumps(
                report,
                ensure_ascii=False,
            ),
            success=success,
        )

        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        return snapshot

    finally:
        db.close()


def get_latest_snapshot(
    site_id: str,
) -> ScanSnapshot | None:
    db = SessionLocal()

    try:
        return (
            db.query(ScanSnapshot)
            .filter(
                ScanSnapshot.site_id == site_id
            )
            .order_by(
                ScanSnapshot.created_at.desc()
            )
            .first()
        )

    finally:
        db.close()


def snapshot_report(
    snapshot: ScanSnapshot | None,
) -> dict | None:
    if snapshot is None:
        return None

    try:
        report = json.loads(
            snapshot.report_json
        )
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(report, dict):
        return None

    return report


def extract_report_issues(
    report: dict,
) -> list[dict]:
    normalized_issues = []

    for category in (
        "seo",
        "conversion",
        "performance",
    ):
        section = report.get(category) or {}

        for issue in section.get("issues", []):
            issue_type = issue.get("type")

            if not issue_type:
                continue

            normalized_issues.append(
                {
                    "fingerprint": (
                        f"{category}:{issue_type}"
                    ),
                    "category": category,
                    "issue_type": issue_type,
                    "severity": issue.get(
                        "severity",
                        "low",
                    ),
                    "message": issue.get(
                        "message",
                        "",
                    ),
                    "recommendation": issue.get(
                        "recommendation",
                    ),
                }
            )

    return normalized_issues


def compare_report_issues(
    previous_report: dict | None,
    current_report: dict,
) -> dict:
    previous_issues = (
        extract_report_issues(previous_report)
        if previous_report
        else []
    )

    current_issues = extract_report_issues(
        current_report
    )

    previous_by_fingerprint = {
        issue["fingerprint"]: issue
        for issue in previous_issues
    }

    current_by_fingerprint = {
        issue["fingerprint"]: issue
        for issue in current_issues
    }

    previous_fingerprints = set(
        previous_by_fingerprint
    )
    current_fingerprints = set(
        current_by_fingerprint
    )

    new_fingerprints = (
        current_fingerprints
        - previous_fingerprints
    )

    resolved_fingerprints = (
        previous_fingerprints
        - current_fingerprints
    )

    persistent_fingerprints = (
        previous_fingerprints
        & current_fingerprints
    )

    return {
        "new": [
            current_by_fingerprint[fingerprint]
            for fingerprint in sorted(
                new_fingerprints
            )
        ],
        "resolved": [
            previous_by_fingerprint[fingerprint]
            for fingerprint in sorted(
                resolved_fingerprints
            )
        ],
        "persistent": [
            current_by_fingerprint[fingerprint]
            for fingerprint in sorted(
                persistent_fingerprints
            )
        ],
    }


def upsert_open_issue(
    site_id: str,
    issue: dict,
) -> LeakIssue:
    db = SessionLocal()

    try:
        now = datetime.now(timezone.utc)

        leak_issue = (
            db.query(LeakIssue)
            .filter(
                LeakIssue.site_id == site_id,
                LeakIssue.fingerprint
                == issue["fingerprint"],
            )
            .first()
        )

        if leak_issue is None:
            leak_issue = LeakIssue(
                issue_id=uuid.uuid4().hex,
                site_id=site_id,
                fingerprint=issue["fingerprint"],
                category=issue["category"],
                issue_type=issue["issue_type"],
                severity=issue["severity"],
                message=issue["message"],
                recommendation=issue.get(
                    "recommendation"
                ),
                status="open",
                first_seen_at=now,
                last_seen_at=now,
            )

            db.add(leak_issue)

        else:
            leak_issue.category = issue["category"]
            leak_issue.issue_type = issue["issue_type"]
            leak_issue.severity = issue["severity"]
            leak_issue.message = issue["message"]
            leak_issue.recommendation = issue.get(
                "recommendation"
            )
            leak_issue.status = "open"
            leak_issue.last_seen_at = now
            leak_issue.resolved_at = None

        db.commit()
        db.refresh(leak_issue)

        return leak_issue

    finally:
        db.close()


def resolve_issue(
    site_id: str,
    fingerprint: str,
) -> LeakIssue | None:
    db = SessionLocal()

    try:
        leak_issue = (
            db.query(LeakIssue)
            .filter(
                LeakIssue.site_id == site_id,
                LeakIssue.fingerprint == fingerprint,
            )
            .first()
        )

        if leak_issue is None:
            return None

        now = datetime.now(timezone.utc)

        leak_issue.status = "resolved"
        leak_issue.resolved_at = now

        db.commit()
        db.refresh(leak_issue)

        return leak_issue

    finally:
        db.close()


def sync_issue_lifecycle(
    site_id: str,
    comparison: dict,
) -> None:
    for issue in comparison.get("new", []):
        upsert_open_issue(
            site_id,
            issue,
        )

    for issue in comparison.get("persistent", []):
        upsert_open_issue(
            site_id,
            issue,
        )

    for issue in comparison.get("resolved", []):
        resolve_issue(
            site_id,
            issue["fingerprint"],
        )


def get_monitored_site(
    site_id: str,
) -> MonitoredSite | None:
    db = SessionLocal()

    try:
        return db.get(
            MonitoredSite,
            site_id,
        )

    finally:
        db.close()


def update_scan_schedule(
    site_id: str,
) -> MonitoredSite | None:
    db = SessionLocal()

    try:
        site = db.get(
            MonitoredSite,
            site_id,
        )

        if site is None:
            return None

        now = datetime.now(timezone.utc)

        site.last_scanned_at = now
        site.next_scan_at = (
            now + timedelta(days=1)
        )

        db.commit()
        db.refresh(site)

        return site

    finally:
        db.close()


async def run_monitoring_scan(
    site_id: str,
) -> dict:
    site = get_monitored_site(
        site_id
    )

    if site is None:
        return {
            "success": False,
            "error": "Monitored site not found.",
        }

    if not site.monitoring_enabled:
        return {
            "success": False,
            "error": "Monitoring is disabled for this site.",
        }

    previous_snapshot = get_latest_snapshot(
        site_id
    )

    previous_report = snapshot_report(
        previous_snapshot
    )

    website_data = await scan_website(
        site.website_url
    )

    if not website_data.get("success"):
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

    current_report = {
        "website": website_data,
        "seo": seo_result,
        "conversion": conversion_result,
        "performance": performance_result,
        "revenue_leak": revenue_leak_result,
    }

    comparison = compare_report_issues(
        previous_report,
        current_report,
    )

    snapshot = persist_monitoring_result(
        site_id=site_id,
        report=current_report,
        comparison=comparison,
    )

    return {
        "success": True,
        "site_id": site_id,
        "snapshot_id": snapshot.snapshot_id,
        "comparison": comparison,
        "report": current_report,
    }


def persist_monitoring_result(
    site_id: str,
    report: dict,
    comparison: dict,
) -> ScanSnapshot:
    db = SessionLocal()

    try:
        now = datetime.now(timezone.utc)

        for issue in (
            comparison.get("new", [])
            + comparison.get("persistent", [])
        ):
            leak_issue = (
                db.query(LeakIssue)
                .filter(
                    LeakIssue.site_id == site_id,
                    LeakIssue.fingerprint == issue["fingerprint"],
                )
                .first()
            )

            if leak_issue is None:
                leak_issue = LeakIssue(
                    issue_id=uuid.uuid4().hex,
                    site_id=site_id,
                    fingerprint=issue["fingerprint"],
                    category=issue["category"],
                    issue_type=issue["issue_type"],
                    severity=issue["severity"],
                    message=issue["message"],
                    recommendation=issue.get("recommendation"),
                    status="open",
                    first_seen_at=now,
                    last_seen_at=now,
                )
                db.add(leak_issue)
            else:
                leak_issue.category = issue["category"]
                leak_issue.issue_type = issue["issue_type"]
                leak_issue.severity = issue["severity"]
                leak_issue.message = issue["message"]
                leak_issue.recommendation = issue.get("recommendation")
                leak_issue.status = "open"
                leak_issue.last_seen_at = now
                leak_issue.resolved_at = None

        for issue in comparison.get("resolved", []):
            leak_issue = (
                db.query(LeakIssue)
                .filter(
                    LeakIssue.site_id == site_id,
                    LeakIssue.fingerprint == issue["fingerprint"],
                )
                .first()
            )

            if leak_issue is not None:
                leak_issue.status = "resolved"
                leak_issue.resolved_at = now

        snapshot = ScanSnapshot(
            snapshot_id=uuid.uuid4().hex,
            site_id=site_id,
            report_json=json.dumps(
                report,
                ensure_ascii=False,
            ),
            success=True,
        )
        db.add(snapshot)

        site = db.get(MonitoredSite, site_id)

        if site is None:
            raise ValueError("Monitored site not found.")

        site.last_scanned_at = now
        site.next_scan_at = now + timedelta(days=1)

        db.commit()
        db.refresh(snapshot)

        return snapshot

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
