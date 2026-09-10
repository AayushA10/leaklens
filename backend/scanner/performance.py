from urllib.parse import urlparse

from playwright.async_api import async_playwright

from scanner.crawler import (
    UnsafeURLError,
    validate_public_url,
)


async def analyze_performance(url: str) -> dict:
    """
    Measure basic website performance using Google Chrome.

    Security:
    - Only public HTTP/HTTPS websites are allowed.
    - Localhost and private networks are blocked.
    - Cloud metadata/link-local addresses are blocked.
    - Browser subrequests are validated.
    - Redirect destinations are validated.

    If performance measurement fails, the category is marked
    unavailable instead of incorrectly returning 100/100.
    """

    result = {
        "status": "unavailable",
        "score": None,
        "load_time_ms": None,
        "dom_content_loaded_ms": None,
        "page_size_kb": None,
        "requests_count": None,
        "issues_count": 0,
        "issues": [],
        "error": None,
    }

    browser = None
    context = None

    # Cache hostname validation results for this individual scan.
    dns_cache: dict[str, bool] = {}

    try:
        # =================================
        # SECURITY VALIDATION
        # =================================

        # Validate the original user-supplied URL before
        # launching or navigating the browser.
        await validate_public_url(
            url,
            dns_cache=dns_cache,
        )

        async with async_playwright() as p:

            # Use locally installed Google Chrome.
            browser = await p.chromium.launch(
                channel="chrome",
                headless=True,
            )

            context = await browser.new_context(
                viewport={
                    "width": 390,
                    "height": 844,
                },
                ignore_https_errors=False,
            )

            # =================================
            # NETWORK / SSRF PROTECTION
            # =================================

            async def safe_route(
                route,
                request,
            ):
                """
                Validate every HTTP/HTTPS browser request.

                This prevents a public website from causing the
                scanner browser to request localhost, private
                networks, cloud metadata endpoints, or other
                blocked network resources.
                """

                request_url = request.url

                try:
                    parsed_request = urlparse(
                        request_url
                    )

                except ValueError:
                    await route.abort(
                        "blockedbyclient"
                    )
                    return

                # Browser-internal resources such as data:, blob:,
                # and about: do not directly target a network host.
                if parsed_request.scheme not in {
                    "http",
                    "https",
                }:
                    await route.continue_()
                    return

                try:
                    await validate_public_url(
                        request_url,
                        dns_cache=dns_cache,
                    )

                except UnsafeURLError:
                    await route.abort(
                        "blockedbyclient"
                    )
                    return

                await route.continue_()

            await context.route(
                "**/*",
                safe_route,
            )

            page = await context.new_page()

            requests_count = 0
            total_bytes = 0

            # =================================
            # REQUEST COUNTER
            # =================================

            def count_request(request):
                nonlocal requests_count

                requests_count += 1

            page.on(
                "request",
                count_request,
            )

            # =================================
            # RESPONSE SIZE ESTIMATION
            # =================================

            async def count_response(response):
                nonlocal total_bytes

                try:
                    headers = (
                        await response.all_headers()
                    )

                    content_length = headers.get(
                        "content-length"
                    )

                    if content_length:
                        total_bytes += int(
                            content_length
                        )

                except Exception:
                    # A response may not expose usable headers.
                    # That should not fail the entire scan.
                    pass

            page.on(
                "response",
                count_response,
            )

            # =================================
            # LOAD PAGE
            # =================================

            response = await page.goto(
                url,
                wait_until="load",
                timeout=45000,
            )

            if response is None:
                raise RuntimeError(
                    "The website did not return a valid response."
                )

            # Validate where the browser actually ended up.
            # This protects against a public URL redirecting
            # toward localhost/private infrastructure.
            await validate_public_url(
                page.url,
                dns_cache=dns_cache,
            )

            await page.wait_for_timeout(
                1000
            )

            # Validate again after the short wait in case
            # client-side JavaScript changed the page URL.
            await validate_public_url(
                page.url,
                dns_cache=dns_cache,
            )

            # =================================
            # PERFORMANCE TIMING
            # =================================

            timing = await page.evaluate(
                """
                () => {
                    const navigation =
                        performance.getEntriesByType(
                            "navigation"
                        )[0];

                    if (!navigation) {
                        return null;
                    }

                    return {
                        loadTime:
                            navigation.loadEventEnd -
                            navigation.startTime,

                        domContentLoaded:
                            navigation.domContentLoadedEventEnd -
                            navigation.startTime
                    };
                }
                """
            )

            if not timing:
                raise RuntimeError(
                    "Browser performance timing was unavailable."
                )

            load_time = round(
                timing.get(
                    "loadTime",
                    0,
                )
            )

            dom_content_loaded = round(
                timing.get(
                    "domContentLoaded",
                    0,
                )
            )

            # =================================
            # FALLBACK RESOURCE SIZE
            # =================================

            if total_bytes == 0:
                resource_size = await page.evaluate(
                    """
                    () => {
                        const resources =
                            performance.getEntriesByType(
                                "resource"
                            );

                        return resources.reduce(
                            (total, resource) => {
                                return total +
                                    (
                                        resource.transferSize ||
                                        resource.encodedBodySize ||
                                        0
                                    );
                            },
                            0
                        );
                    }
                    """
                )

                total_bytes = int(
                    resource_size or 0
                )

            # =================================
            # SAVE RAW METRICS
            # =================================

            result["load_time_ms"] = (
                load_time
            )

            result[
                "dom_content_loaded_ms"
            ] = dom_content_loaded

            result[
                "requests_count"
            ] = requests_count

            result["page_size_kb"] = round(
                total_bytes / 1024,
                2,
            )

            result["status"] = "available"

            # =================================
            # CLEAN BROWSER SHUTDOWN
            # =================================

            await context.close()
            context = None

            await browser.close()
            browser = None

    except UnsafeURLError as exc:
        result["status"] = "unavailable"
        result["score"] = None
        result["load_time_ms"] = None
        result["dom_content_loaded_ms"] = None
        result["page_size_kb"] = None
        result["requests_count"] = None
        result["issues_count"] = 0
        result["issues"] = []
        result["error"] = (
            f"Unsafe URL blocked: {exc}"
        )

        if context:
            try:
                await context.close()
            except Exception:
                pass

            context = None

        if browser:
            try:
                await browser.close()
            except Exception:
                pass

            browser = None

        return result

    except Exception as exc:
        result["status"] = "unavailable"
        result["score"] = None
        result["load_time_ms"] = None
        result["dom_content_loaded_ms"] = None
        result["page_size_kb"] = None
        result["requests_count"] = None
        result["issues_count"] = 0
        result["issues"] = []
        result["error"] = str(exc)

        if context:
            try:
                await context.close()
            except Exception:
                pass

            context = None

        if browser:
            try:
                await browser.close()
            except Exception:
                pass

            browser = None

        return result

    # =================================
    # PERFORMANCE ANALYSIS
    # =================================

    issues = []

    load_time = result.get(
        "load_time_ms"
    )

    # =================================
    # LOAD TIME
    # =================================

    if load_time is not None:

        if load_time > 5000:
            issues.append(
                {
                    "type": "very_slow_load",
                    "severity": "high",
                    "category": "performance",
                    "message": (
                        f"The page took approximately "
                        f"{load_time / 1000:.1f} seconds "
                        f"to finish loading in this scan."
                    ),
                    "business_impact": (
                        "Slow loading can create friction "
                        "before visitors interact with the page."
                    ),
                    "recommendation": (
                        "Review large images, JavaScript, "
                        "third-party scripts, caching, and "
                        "server response performance."
                    ),
                }
            )

        elif load_time > 3000:
            issues.append(
                {
                    "type": "slow_load",
                    "severity": "medium",
                    "category": "performance",
                    "message": (
                        f"The page took approximately "
                        f"{load_time / 1000:.1f} seconds "
                        f"to finish loading in this scan."
                    ),
                    "business_impact": (
                        "Visitors on slower devices or "
                        "connections may experience friction."
                    ),
                    "recommendation": (
                        "Optimize heavy assets and reduce "
                        "unnecessary scripts where possible."
                    ),
                }
            )

    # =================================
    # PAGE SIZE
    # =================================

    page_size = result.get(
        "page_size_kb"
    )

    if page_size is not None:

        if page_size > 5000:
            issues.append(
                {
                    "type": "very_large_page",
                    "severity": "medium",
                    "category": "performance",
                    "message": (
                        f"The scan transferred approximately "
                        f"{page_size / 1024:.1f} MB "
                        f"of resources."
                    ),
                    "business_impact": (
                        "Large pages may load slowly on mobile "
                        "or limited-bandwidth connections."
                    ),
                    "recommendation": (
                        "Compress images, reduce unnecessary "
                        "assets, and lazy-load non-critical media."
                    ),
                }
            )

        elif page_size > 3000:
            issues.append(
                {
                    "type": "large_page",
                    "severity": "low",
                    "category": "performance",
                    "message": (
                        f"The scan transferred approximately "
                        f"{page_size / 1024:.1f} MB "
                        f"of resources."
                    ),
                    "business_impact": (
                        "Heavy pages can increase loading time "
                        "for some visitors."
                    ),
                    "recommendation": (
                        "Review images, fonts, scripts, "
                        "and other large resources."
                    ),
                }
            )

    # =================================
    # REQUEST COUNT
    # =================================

    requests_count = result.get(
        "requests_count"
    )

    if (
        requests_count is not None
        and requests_count > 150
    ):
        issues.append(
            {
                "type": "high_request_count",
                "severity": "low",
                "category": "performance",
                "message": (
                    f"The page made approximately "
                    f"{requests_count} network requests."
                ),
                "business_impact": (
                    "A large number of resources can increase "
                    "page complexity and loading overhead."
                ),
                "recommendation": (
                    "Review third-party scripts and remove "
                    "unnecessary page resources."
                ),
            }
        )

    # =================================
    # PERFORMANCE SCORE
    # =================================

    penalties = {
        "critical": 30,
        "high": 20,
        "medium": 10,
        "low": 5,
    }

    score = 100

    for issue in issues:
        score -= penalties.get(
            issue.get(
                "severity"
            ),
            0,
        )

    result["score"] = max(
        0,
        score,
    )

    result["issues"] = issues

    result["issues_count"] = len(
        issues
    )

    return result