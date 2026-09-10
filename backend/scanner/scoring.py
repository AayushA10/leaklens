def calculate_revenue_leak_score(
    seo_result: dict,
    conversion_result: dict,
    performance_result: dict,
) -> dict:
    """
    Calculate the overall Revenue Leak Score.

    Combines available category scores using normalized weights.
    Unavailable categories are excluded from the weighted calculation
    instead of being treated as 0 or 100.

    Severity-based safeguards ensure serious findings cannot be hidden
    by strong scores in unrelated categories.

    Higher health score = healthier website.
    Higher leak score = greater potential website friction.
    """

    # ---------------------------------
    # RAW CATEGORY SCORES
    # ---------------------------------

    seo_score = seo_result.get("score")
    conversion_score = conversion_result.get("score")
    performance_score = performance_result.get("score")

    # ---------------------------------
    # CATEGORY WEIGHTS
    # ---------------------------------

    category_weights = {
        "seo": 0.25,
        "conversion": 0.40,
        "performance": 0.35,
    }

    category_results = {
        "seo": seo_score,
        "conversion": conversion_score,
        "performance": performance_score,
    }

    # ---------------------------------
    # AVAILABLE CATEGORY SCORES
    # ---------------------------------

    available_categories = {
        category: score
        for category, score in category_results.items()
        if isinstance(score, (int, float))
    }

    unavailable_categories = [
        category
        for category, score in category_results.items()
        if not isinstance(score, (int, float))
    ]

    # ---------------------------------
    # NORMALIZED WEIGHTED HEALTH SCORE
    # ---------------------------------

    if available_categories:
        available_weight_total = sum(
            category_weights[category]
            for category in available_categories
        )

        weighted_health_score = round(
            sum(
                score * category_weights[category]
                for category, score in available_categories.items()
            )
            / available_weight_total
        )
    else:
        weighted_health_score = None

    if weighted_health_score is not None:
        weighted_health_score = max(
            0,
            min(100, weighted_health_score),
        )

    # ---------------------------------
    # COLLECT ALL ISSUES
    # ---------------------------------

    all_issues = (
        seo_result.get("issues", [])
        + conversion_result.get("issues", [])
        + performance_result.get("issues", [])
    )

    severity_order = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
    }

    sorted_issues = sorted(
        all_issues,
        key=lambda issue: severity_order.get(
            issue.get("severity", "low"),
            0,
        ),
        reverse=True,
    )

    top_issues = sorted_issues[:3]

    # ---------------------------------
    # ISSUE COUNTS
    # ---------------------------------

    critical_count = sum(
        1
        for issue in all_issues
        if issue.get("severity") == "critical"
    )

    high_count = sum(
        1
        for issue in all_issues
        if issue.get("severity") == "high"
    )

    medium_count = sum(
        1
        for issue in all_issues
        if issue.get("severity") == "medium"
    )

    low_count = sum(
        1
        for issue in all_issues
        if issue.get("severity") == "low"
    )

    # ---------------------------------
    # BASE LEAK SCORE
    # ---------------------------------

    if weighted_health_score is not None:
        leak_score = 100 - weighted_health_score
    else:
        leak_score = None

    # ---------------------------------
    # SEVERITY SAFEGUARDS
    # ---------------------------------
    #
    # Serious problems should create a minimum
    # level of risk even if other categories score well.
    #

    if leak_score is not None:

        if critical_count >= 1:
            leak_score = max(
                leak_score,
                50,
            )

        elif high_count >= 3:
            leak_score = max(
                leak_score,
                40,
            )

        elif high_count >= 2:
            leak_score = max(
                leak_score,
                32,
            )

        elif high_count == 1:
            leak_score = max(
                leak_score,
                24,
            )

        # Several medium issues should also matter.
        if medium_count >= 5:
            leak_score = max(
                leak_score,
                25,
            )

        elif medium_count >= 3:
            leak_score = max(
                leak_score,
                18,
            )

        leak_score = max(
            0,
            min(100, round(leak_score)),
        )

        health_score = 100 - leak_score

    else:
        health_score = None

    # ---------------------------------
    # RISK LEVEL
    # ---------------------------------

    if leak_score is None:
        risk_level = "Unavailable"

    elif leak_score <= 10:
        risk_level = "Excellent"

    elif leak_score <= 25:
        risk_level = "Low"

    elif leak_score <= 45:
        risk_level = "Moderate"

    elif leak_score <= 65:
        risk_level = "High"

    else:
        risk_level = "Critical"

    # ---------------------------------
    # CATEGORY SCORES
    # ---------------------------------

    category_scores = {
        "seo": seo_score,
        "conversion": conversion_score,
        "performance": performance_score,
    }

    return {
        "health_score": health_score,
        "leak_score": leak_score,
        "risk_level": risk_level,
        "category_scores": category_scores,
        "available_categories": list(
            available_categories.keys()
        ),
        "unavailable_categories": unavailable_categories,
        "total_issues": len(all_issues),
        "critical_issues": critical_count,
        "high_issues": high_count,
        "medium_issues": medium_count,
        "low_issues": low_count,
        "top_issues": top_issues,
    }