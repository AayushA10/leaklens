import time
import os
import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


CTA_KEYWORDS = [
    "book now",
    "book",
    "schedule",
    "schedule now",
    "contact us",
    "contact",
    "get quote",
    "get a quote",
    "request quote",
    "request a quote",
    "get started",
    "start now",
    "buy now",
    "shop now",
    "order now",
    "sign up",
    "register",
    "learn more",
    "call now",
    "apply now",
    "reserve",
    "make appointment",
    "request appointment",
]


BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata",
    "metadata.google.internal",
}


ALLOWED_PORTS = {
    None,
    80,
    443,
}


class UnsafeURLError(ValueError):
    """
    Raised when a URL is not safe for the public website scanner.
    """


def _normalize_hostname(hostname: str) -> str:
    return hostname.strip().lower().rstrip(".")


def _is_public_ip(ip_string: str) -> bool:
    """
    Return True only for globally routable public IP addresses.

    This rejects:
    - loopback
    - private networks
    - link-local
    - multicast
    - reserved ranges
    - unspecified addresses
    - cloud metadata/link-local ranges
    """

    try:
        ip = ipaddress.ip_address(ip_string)
    except ValueError:
        return False

    # IPv4-mapped IPv6 address, for example:
    # ::ffff:127.0.0.1
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped

    return ip.is_global


async def _resolve_hostname(hostname: str) -> set[str]:
    """
    Resolve a hostname without blocking the FastAPI event loop.
    """

    def resolve() -> set[str]:
        addresses = set()

        results = socket.getaddrinfo(
            hostname,
            None,
            type=socket.SOCK_STREAM,
        )

        for result in results:
            sockaddr = result[4]

            if sockaddr:
                addresses.add(sockaddr[0])

        return addresses

    try:
        dns_started = time.monotonic()
        addresses = await asyncio.to_thread(resolve)

        print(
            f"[LeakLens DNS] host={hostname} "
            f"time={time.monotonic() - dns_started:.2f}s",
            flush=True,
        )

        return addresses

    except socket.gaierror as exc:
        raise UnsafeURLError(
            f"Unable to resolve hostname: {hostname}"
        ) from exc


async def validate_public_url(
    url: str,
    dns_cache: dict[str, bool] | None = None,
    dns_inflight: dict[str, asyncio.Task] | None = None,
) -> None:
    """
    Validate that a URL points to a normal public website.

    Protects LeakLens from being used to reach:
    - localhost
    - private LAN resources
    - loopback services
    - link-local resources
    - cloud metadata services
    - non-HTTP protocols
    """

    if not isinstance(url, str) or not url.strip():
        raise UnsafeURLError(
            "A valid website URL is required."
        )

    url = url.strip()

    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise UnsafeURLError(
            "Invalid website URL."
        ) from exc

    if parsed.scheme.lower() not in {
        "http",
        "https",
    }:
        raise UnsafeURLError(
            "Only http:// and https:// URLs are allowed."
        )

    if parsed.username or parsed.password:
        raise UnsafeURLError(
            "URLs containing usernames or passwords are not allowed."
        )

    hostname = parsed.hostname

    if not hostname:
        raise UnsafeURLError(
            "The URL must contain a valid hostname."
        )

    hostname = _normalize_hostname(
        hostname
    )

    if (
        hostname in BLOCKED_HOSTNAMES
        or hostname.endswith(".localhost")
        or hostname.endswith(".local")
        or hostname.endswith(".internal")
    ):
        raise UnsafeURLError(
            "Local or internal hostnames are not allowed."
        )

    try:
        port = parsed.port
    except ValueError as exc:
        raise UnsafeURLError(
            "Invalid URL port."
        ) from exc

    if port not in ALLOWED_PORTS:
        raise UnsafeURLError(
            "Only standard HTTP and HTTPS ports are allowed."
        )

    # If user supplied an IP directly, validate it immediately.
    try:
        direct_ip = ipaddress.ip_address(
            hostname
        )

        if not _is_public_ip(
            str(direct_ip)
        ):
            raise UnsafeURLError(
                "Private, local, or reserved IP addresses are not allowed."
            )

        return

    except ValueError:
        # Normal hostname, resolve below.
        pass

    if (
        dns_cache is not None
        and hostname in dns_cache
    ):
        if not dns_cache[hostname]:
            raise UnsafeURLError(
                "Hostname resolves to a blocked IP address."
            )

        return

    if dns_inflight is not None:
        task = dns_inflight.get(hostname)

        if task is None:
            task = asyncio.create_task(
                _resolve_hostname(hostname)
            )
            dns_inflight[hostname] = task

        try:
            addresses = await task
        finally:
            if (
                dns_inflight.get(hostname)
                is task
                and task.done()
            ):
                dns_inflight.pop(
                    hostname,
                    None,
                )
    else:
        addresses = await _resolve_hostname(
            hostname
        )

    if not addresses:
        raise UnsafeURLError(
            "Hostname did not resolve to an IP address."
        )

    all_public = all(
        _is_public_ip(address)
        for address in addresses
    )

    if dns_cache is not None:
        dns_cache[hostname] = all_public

    if not all_public:
        raise UnsafeURLError(
            "Hostname resolves to a private, local, or reserved IP address."
        )


def _populate_result_from_html(
    result: dict,
    html: str,
    final_url: str,
) -> None:
    """
    Populate SEO and conversion fields from HTML.
    Shared by browser scans and HTTP fallback scans.
    """

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    # Page title
    if (
        soup.title
        and soup.title.string
    ):
        result["title"] = (
            soup.title.string.strip()
        )

    # Meta description
    meta_description = soup.find(
        "meta",
        attrs={
            "name": "description"
        },
    )

    if meta_description:
        content = meta_description.get(
            "content"
        )

        if content:
            result[
                "meta_description"
            ] = content.strip()

    # H1 headings
    result["h1"] = [
        heading.get_text(
            " ",
            strip=True,
        )
        for heading
        in soup.find_all("h1")
        if heading.get_text(
            " ",
            strip=True,
        )
    ]

    # Links
    links = soup.find_all(
        "a",
        href=True,
    )

    result["links_count"] = len(
        links
    )

    parsed_current_url = urlparse(
        final_url
    )

    current_domain = (
        parsed_current_url
        .netloc
        .lower()
    )

    internal_links = 0
    external_links = 0
    detected_ctas = []

    for link in links:
        href = (
            link.get(
                "href",
                "",
            )
            .strip()
        )

        text = link.get_text(
            " ",
            strip=True,
        )

        if not href:
            continue

        href_lower = href.lower()

        if href_lower.startswith(
            "tel:"
        ):
            result[
                "has_phone_link"
            ] = True

        if href_lower.startswith(
            "mailto:"
        ):
            result[
                "has_email_link"
            ] = True

        normalized_text = (
            text.lower().strip()
        )

        if normalized_text:
            for keyword in CTA_KEYWORDS:
                if (
                    keyword
                    in normalized_text
                ):
                    detected_ctas.append(
                        {
                            "text": text,
                            "href": href,
                            "element": "link",
                        }
                    )
                    break

        absolute_url = urljoin(
            final_url,
            href,
        )

        parsed_link = urlparse(
            absolute_url
        )

        if (
            parsed_link.scheme
            not in {
                "http",
                "https",
            }
        ):
            continue

        if (
            parsed_link.netloc.lower()
            == current_domain
        ):
            internal_links += 1
        else:
            external_links += 1

    result[
        "internal_links_count"
    ] = internal_links

    result[
        "external_links_count"
    ] = external_links

    # Images
    result[
        "images_count"
    ] = len(
        soup.find_all("img")
    )

    # Forms
    result[
        "forms_count"
    ] = len(
        soup.find_all("form")
    )

    # Buttons
    buttons = soup.find_all(
        "button"
    )

    result[
        "buttons_count"
    ] = len(buttons)

    for button in buttons:
        text = button.get_text(
            " ",
            strip=True,
        )

        normalized_text = (
            text.lower().strip()
        )

        if not normalized_text:
            continue

        for keyword in CTA_KEYWORDS:
            if (
                keyword
                in normalized_text
            ):
                detected_ctas.append(
                    {
                        "text": text,
                        "href": None,
                        "element": "button",
                    }
                )
                break

    # Remove duplicate CTAs
    unique_ctas = []
    seen = set()

    for cta in detected_ctas:
        key = (
            cta["text"].lower(),
            cta["href"],
            cta["element"],
        )

        if key in seen:
            continue

        seen.add(key)
        unique_ctas.append(cta)

    result["ctas"] = unique_ctas
    result["cta_count"] = len(
        unique_ctas
    )


async def _fetch_html_fallback(
    url: str,
    dns_cache: dict[str, bool],
) -> tuple[str, str, int]:
    """
    Fetch public HTML without a browser.

    Redirects are handled manually so every destination
    is validated before LeakLens connects to it.
    """

    current_url = url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; LeakLens/1.0; "
            "+https://leaklens-beige.vercel.app)"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
    }

    timeout = httpx.Timeout(
        10.0,
        connect=5.0,
    )

    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=timeout,
        headers=headers,
    ) as client:

        for _ in range(6):
            await validate_public_url(
                current_url,
                dns_cache=dns_cache,
            )

            response = await client.get(
                current_url
            )

            if response.status_code in {
                301,
                302,
                303,
                307,
                308,
            }:
                location = response.headers.get(
                    "location"
                )

                if not location:
                    raise RuntimeError(
                        "Redirect response did not include a location."
                    )

                next_url = urljoin(
                    current_url,
                    location,
                )

                await validate_public_url(
                    next_url,
                    dns_cache=dns_cache,
                )

                current_url = next_url
                continue

            response.raise_for_status()

            content_type = (
                response.headers.get(
                    "content-type",
                    "",
                )
                .lower()
            )

            if (
                content_type
                and "text/html" not in content_type
                and "application/xhtml+xml"
                not in content_type
            ):
                raise RuntimeError(
                    "Fallback response was not HTML."
                )

            return (
                response.text,
                str(response.url),
                response.status_code,
            )

    raise RuntimeError(
        "Too many redirects during fallback scan."
    )


async def scan_website(url: str) -> dict:
    """
    Visit a public website and collect information for
    SEO and conversion analysis.

    Includes SSRF protection so LeakLens cannot be used
    to access localhost, private networks, cloud metadata
    services, or other internal resources.
    """

    scan_started = time.monotonic()

    result = {
        "url": url,
        "final_url": None,
        "status_code": None,
        "success": False,
        "title": None,
        "meta_description": None,
        "h1": [],
        "links_count": 0,
        "internal_links_count": 0,
        "external_links_count": 0,
        "images_count": 0,
        "forms_count": 0,
        "buttons_count": 0,
        "cta_count": 0,
        "ctas": [],
        "has_phone_link": False,
        "has_email_link": False,
        "performance_raw": None,
        "error": None,
    }

    browser = None
    context = None
    page = None

    # Cache DNS decisions during this individual scan.
    dns_cache: dict[str, bool] = {}
    dns_inflight: dict[str, asyncio.Task] = {}

    try:
        # ------------------------------------------------
        # Validate original URL before opening the browser
        # ------------------------------------------------
        await validate_public_url(
            url,
            dns_cache=dns_cache,
        )

        async with async_playwright() as p:

            browser_channel = os.getenv(
                "BROWSER_CHANNEL",
                "",
            ).strip()

            launch_options = {
                "headless": True,
            }

            if browser_channel:
                launch_options["channel"] = browser_channel

            browser_launch_started = time.monotonic()

            browser = await p.chromium.launch(
                **launch_options
            )

            print(
                f"[LeakLens timing] browser_launch="
                f"{time.monotonic() - browser_launch_started:.2f}s",
                flush=True,
            )

            context = await browser.new_context(
                viewport={
                    "width": 1440,
                    "height": 900,
                },
                ignore_https_errors=False,
            )

            # ------------------------------------------------
            # Protect browser requests and redirects
            # ------------------------------------------------
            async def safe_route(
                route,
                request,
            ):
                request_url = request.url

                parsed_request = urlparse(
                    request_url
                )

                def is_normal_route_shutdown(exc: Exception) -> bool:
                    error_text = str(exc)

                    return (
                        "Route is already handled" in error_text
                        or (
                            "Target page, context or browser has been closed"
                            in error_text
                        )
                    )

                # data:, blob:, about:, etc. may be normal browser
                # resources and cannot access network hosts directly.
                if parsed_request.scheme not in {
                    "http",
                    "https",
                }:
                    try:
                        await route.continue_()
                    except Exception as exc:
                        if not is_normal_route_shutdown(exc):
                            raise
                    return

                try:
                    await validate_public_url(
                        request_url,
                        dns_cache=dns_cache,
                        dns_inflight=dns_inflight,
                    )

                except UnsafeURLError:
                    try:
                        await route.abort(
                            "blockedbyclient"
                        )
                    except Exception as exc:
                        if not is_normal_route_shutdown(exc):
                            raise
                    return

                try:
                    await route.continue_()
                except Exception as exc:
                    if not is_normal_route_shutdown(exc):
                        raise

            page = await context.new_page()

            await page.route(
                "**/*",
                safe_route,
            )

            requests_count = 0
            total_bytes = 0

            def count_request(request):
                nonlocal requests_count
                requests_count += 1

            async def count_response(response):
                nonlocal total_bytes

                try:
                    headers = await response.all_headers()
                    content_length = headers.get(
                        "content-length"
                    )

                    if content_length:
                        total_bytes += int(
                            content_length
                        )

                except Exception:
                    pass

            page.on(
                "request",
                count_request,
            )

            page.on(
                "response",
                count_response,
            )

            # Use one fast browser attempt.
            # If browser navigation fails, the safe HTTP fallback
            # handles the page instead of making the user wait
            # through another full browser timeout.
            navigation_started = time.monotonic()

            try:
                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=6000,
                )
            finally:
                print(
                    f"[LeakLens timing] navigation="
                    f"{time.monotonic() - navigation_started:.2f}s",
                    flush=True,
                )

            # Give dynamic content a short opportunity to render.
            await page.wait_for_timeout(
                1000
            )

            final_url = page.url

            # Explicitly validate final URL too.
            # This protects against malicious redirect chains.
            await validate_public_url(
                final_url,
                dns_cache=dns_cache,
            )

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

            if timing:
                load_time = round(
                    timing.get(
                        "loadTime",
                        0,
                    )
                )

                if load_time <= 0:
                    load_time = round(
                        timing.get(
                            "domContentLoaded",
                            0,
                        )
                    )

                dom_content_loaded = round(
                    timing.get(
                        "domContentLoaded",
                        0,
                    )
                )

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

                result["performance_raw"] = {
                    "load_time_ms": load_time,
                    "dom_content_loaded_ms": dom_content_loaded,
                    "page_size_kb": round(
                        total_bytes / 1024,
                        2,
                    ),
                    "requests_count": requests_count,
                }

            result["final_url"] = (
                final_url
            )

            if response:
                result["status_code"] = (
                    response.status
                )

            html = await page.content()

            _populate_result_from_html(
                result,
                html,
                final_url,
            )

            result["success"] = True

            await page.unroute_all(
                behavior="wait"
            )

            await page.close()
            page = None

            await context.close()
            context = None

            await browser.close()
            browser = None

    except UnsafeURLError as exc:
        result["error"] = (
            f"Unsafe URL blocked: {exc}"
        )

    except Exception as exc:
        browser_error = str(exc)
        print(
            f"[LeakLens browser fallback] {url}: "
            f"{type(exc).__name__}: {browser_error}",
            flush=True,
        )

        # Browser scans can fail because of CDN/browser-specific
        # behavior even when the public HTML is still reachable.
        # Try a safe HTTP fallback before returning an error.
        try:
            fallback_started = time.monotonic()

            (
                fallback_html,
                fallback_url,
                fallback_status,
            ) = await _fetch_html_fallback(
                url,
                dns_cache,
            )

            print(
                f"[LeakLens timing] http_fallback="
                f"{time.monotonic() - fallback_started:.2f}s",
                flush=True,
            )

            result["final_url"] = fallback_url
            result["status_code"] = fallback_status
            result["performance_raw"] = None

            _populate_result_from_html(
                result,
                fallback_html,
                fallback_url,
            )

            result["success"] = True
            result["error"] = None

        except UnsafeURLError as fallback_exc:
            result["error"] = (
                f"Unsafe URL blocked: {fallback_exc}"
            )

        except Exception:
            if (
                "ERR_HTTP2_PROTOCOL_ERROR" in browser_error
                or "Timeout" in browser_error
                or "403" in browser_error
            ):
                result["error"] = (
                    "This website could not be fully scanned right now. "
                    "Please try again in a moment."
                )
            else:
                result["error"] = (
                    "We could not scan this website right now. "
                    "Please try again in a moment."
                )

    finally:
        print(
            f"[LeakLens timing] total_scan="
            f"{time.monotonic() - scan_started:.2f}s",
            flush=True,
        )

        if page:
            try:
                await page.unroute_all(
                    behavior="wait"
                )
                await page.close()
            except Exception:
                pass

        if context:
            try:
                await context.close()
            except Exception:
                pass

        if browser:
            try:
                await browser.close()
            except Exception:
                pass

    return result
