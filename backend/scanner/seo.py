def analyze_seo(scan_data: dict) -> dict:
    """
    Analyze basic SEO signals from crawler data
    and return structured issues.
    """

    issues = []

    title = scan_data.get("title")
    meta_description = scan_data.get("meta_description")
    h1_list = scan_data.get("h1", [])
    status_code = scan_data.get("status_code")

    # -------------------------
    # Status code check
    # -------------------------
    if status_code and status_code != 200:
        issues.append(
            {
                "type": "status_code",
                "severity": "critical",
                "message": f"Page returned HTTP status code {status_code}.",
                "recommendation": "Ensure the page loads successfully with a 200 status code.",
            }
        )

    # -------------------------
    # Title checks
    # -------------------------
    if not title:
        issues.append(
            {
                "type": "missing_title",
                "severity": "high",
                "message": "The page does not have a title tag.",
                "recommendation": "Add a descriptive title that clearly explains the page content.",
            }
        )
    else:
        title_length = len(title)

        if title_length < 30:
            issues.append(
                {
                    "type": "short_title",
                    "severity": "medium",
                    "message": f"The page title is short ({title_length} characters).",
                    "recommendation": "Consider using a more descriptive title between roughly 30 and 60 characters.",
                }
            )

        elif title_length > 60:
            issues.append(
                {
                    "type": "long_title",
                    "severity": "medium",
                    "message": f"The page title is long ({title_length} characters).",
                    "recommendation": "Consider shortening the title so important wording is less likely to be truncated in search results.",
                }
            )

    # -------------------------
    # Meta description checks
    # -------------------------
    if not meta_description:
        issues.append(
            {
                "type": "missing_meta_description",
                "severity": "medium",
                "message": "The page does not have a meta description.",
                "recommendation": "Add a concise description explaining what the page offers.",
            }
        )
    else:
        description_length = len(meta_description)

        if description_length < 70:
            issues.append(
                {
                    "type": "short_meta_description",
                    "severity": "low",
                    "message": f"The meta description is short ({description_length} characters).",
                    "recommendation": "Consider expanding it so it better explains the page value.",
                }
            )

        elif description_length > 160:
            issues.append(
                {
                    "type": "long_meta_description",
                    "severity": "low",
                    "message": f"The meta description is long ({description_length} characters).",
                    "recommendation": "Consider shortening it to make the key message clearer in search results.",
                }
            )

    # -------------------------
    # H1 checks
    # -------------------------
    if len(h1_list) == 0:
        issues.append(
            {
                "type": "missing_h1",
                "severity": "high",
                "message": "The page does not contain an H1 heading.",
                "recommendation": "Add one clear H1 that describes the main purpose of the page.",
            }
        )

    elif len(h1_list) > 1:
        issues.append(
            {
                "type": "multiple_h1",
                "severity": "medium",
                "message": f"The page contains {len(h1_list)} H1 headings.",
                "recommendation": "Keep the page structure clear and ensure the primary heading is obvious.",
            }
        )

    # -------------------------
    # Internal linking check
    # -------------------------
    internal_links = scan_data.get("internal_links_count", 0)

    if internal_links == 0:
        issues.append(
            {
                "type": "no_internal_links",
                "severity": "medium",
                "message": "No internal links were detected on this page.",
                "recommendation": "Add relevant links to important pages on the same website.",
            }
        )

    # -------------------------
    # Basic overall SEO score
    # -------------------------
    score = 100

    severity_penalties = {
        "critical": 25,
        "high": 15,
        "medium": 8,
        "low": 3,
    }

    for issue in issues:
        score -= severity_penalties.get(issue["severity"], 0)

    score = max(score, 0)

    return {
        "score": score,
        "issues_count": len(issues),
        "issues": issues,
    }