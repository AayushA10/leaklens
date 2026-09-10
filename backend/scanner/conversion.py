def analyze_conversion(scan_data: dict) -> dict:
    """
    Analyze conversion and lead-generation signals.

    The goal is to identify potential friction that could cause
    a business website to lose enquiries, bookings, or customers.
    """

    issues = []

    forms_count = scan_data.get("forms_count", 0)
    buttons_count = scan_data.get("buttons_count", 0)
    cta_count = scan_data.get("cta_count", 0)

    internal_links_count = scan_data.get(
        "internal_links_count",
        0,
    )

    has_phone_link = scan_data.get(
        "has_phone_link",
        False,
    )

    has_email_link = scan_data.get(
        "has_email_link",
        False,
    )

    # ---------------------------------
    # CTA CHECK
    # ---------------------------------

    if cta_count == 0:
        issues.append(
            {
                "type": "missing_clear_cta",
                "severity": "high",
                "category": "conversion",
                "message": (
                    "No clear call-to-action was detected "
                    "on this page."
                ),
                "business_impact": (
                    "Visitors may understand the website but "
                    "not know what action to take next, which "
                    "can reduce leads, bookings, or purchases."
                ),
                "recommendation": (
                    "Add a clear action such as 'Book Now', "
                    "'Get a Quote', 'Contact Us', "
                    "'Schedule', or 'Get Started'."
                ),
            }
        )

    # ---------------------------------
    # LEAD CAPTURE CHECK
    # ---------------------------------

    if (
        forms_count == 0
        and not has_phone_link
        and not has_email_link
    ):
        issues.append(
            {
                "type": "limited_contact_options",
                "severity": "medium",
                "category": "conversion",
                "message": (
                    "No form, clickable phone number, or "
                    "clickable email address was detected."
                ),
                "business_impact": (
                    "Potential customers may have difficulty "
                    "contacting the business directly from "
                    "this page."
                ),
                "recommendation": (
                    "Provide at least one obvious contact "
                    "method such as a form, phone link, "
                    "email link, or booking flow."
                ),
            }
        )

    # ---------------------------------
    # CUSTOMER JOURNEY CHECK
    # ---------------------------------

    if internal_links_count == 0:
        issues.append(
            {
                "type": "weak_customer_journey",
                "severity": "medium",
                "category": "conversion",
                "message": (
                    "No internal navigation links were "
                    "detected."
                ),
                "business_impact": (
                    "Visitors may struggle to move toward "
                    "services, products, pricing, booking, "
                    "or contact pages."
                ),
                "recommendation": (
                    "Create clear internal paths toward "
                    "important conversion pages."
                ),
            }
        )

    # ---------------------------------
    # INTERACTION CHECK
    # ---------------------------------

    if buttons_count == 0 and cta_count == 0:
        issues.append(
            {
                "type": "low_interaction_signal",
                "severity": "low",
                "category": "conversion",
                "message": (
                    "Very few obvious interactive conversion "
                    "elements were detected."
                ),
                "business_impact": (
                    "The page may feel informational rather "
                    "than action-oriented."
                ),
                "recommendation": (
                    "Consider adding prominent interactive "
                    "elements that guide visitors toward "
                    "the next step."
                ),
            }
        )

    # ---------------------------------
    # POSITIVE SIGNALS
    # ---------------------------------

    strengths = []

    if cta_count > 0:
        strengths.append(
            f"{cta_count} call-to-action element(s) detected."
        )

    if forms_count > 0:
        strengths.append(
            f"{forms_count} form(s) detected."
        )

    if has_phone_link:
        strengths.append(
            "Clickable phone contact detected."
        )

    if has_email_link:
        strengths.append(
            "Clickable email contact detected."
        )

    if internal_links_count > 0:
        strengths.append(
            "Internal customer journey links detected."
        )

    # ---------------------------------
    # SCORE
    # ---------------------------------

    score = 100

    penalties = {
        "critical": 30,
        "high": 20,
        "medium": 10,
        "low": 5,
    }

    for issue in issues:
        score -= penalties.get(
            issue["severity"],
            0,
        )

    score = max(score, 0)

    return {
        "score": score,
        "issues_count": len(issues),
        "issues": issues,
        "strengths": strengths,
    }