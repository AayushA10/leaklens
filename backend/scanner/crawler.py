import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

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
        return await asyncio.to_thread(resolve)

    except socket.gaierror as exc:
        raise UnsafeURLError(
            f"Unable to resolve hostname: {hostname}"
        ) from exc


async def validate_public_url(
    url: str,
    dns_cache: dict[str, bool] | None = None,
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


async def scan_website(url: str) -> dict:
    """
    Visit a public website and collect information for
    SEO and conversion analysis.

    Includes SSRF protection so LeakLens cannot be used
    to access localhost, private networks, cloud metadata
    services, or other internal resources.
    """

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
        "error": None,
    }

    browser = None
    context = None

    # Cache DNS decisions during this individual scan.
    dns_cache: dict[str, bool] = {}

    try:
        # ------------------------------------------------
        # Validate original URL before opening the browser
        # ------------------------------------------------
        await validate_public_url(
            url,
            dns_cache=dns_cache,
        )

        async with async_playwright() as p:

            browser = await p.chromium.launch(
                channel="chrome",
                headless=True,
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

                # data:, blob:, about:, etc. may be normal browser
                # resources and cannot access network hosts directly.
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

            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            # Give dynamic content a short opportunity to render.
            await page.wait_for_timeout(
                1500
            )

            final_url = page.url

            # Explicitly validate final URL too.
            # This protects against malicious redirect chains.
            await validate_public_url(
                final_url,
                dns_cache=dns_cache,
            )

            result["final_url"] = (
                final_url
            )

            if response:
                result["status_code"] = (
                    response.status
                )

            html = await page.content()

            soup = BeautifulSoup(
                html,
                "html.parser",
            )

            # -------------------------
            # Page title
            # -------------------------
            if (
                soup.title
                and soup.title.string
            ):
                result["title"] = (
                    soup.title.string.strip()
                )

            # -------------------------
            # Meta description
            # -------------------------
            meta_description = soup.find(
                "meta",
                attrs={
                    "name": "description"
                },
            )

            if meta_description:
                content = (
                    meta_description.get(
                        "content"
                    )
                )

                if content:
                    result[
                        "meta_description"
                    ] = content.strip()

            # -------------------------
            # H1 headings
            # -------------------------
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

            # -------------------------
            # Links
            # -------------------------
            links = soup.find_all(
                "a",
                href=True,
            )

            result["links_count"] = (
                len(links)
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

                href_lower = (
                    href.lower()
                )

                # -------------------------
                # Phone / email detection
                # -------------------------
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

                # -------------------------
                # CTA detection
                # -------------------------
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

                # -------------------------
                # Internal/external links
                # -------------------------
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

            # -------------------------
            # Images
            # -------------------------
            images = soup.find_all(
                "img"
            )

            result[
                "images_count"
            ] = len(images)

            # -------------------------
            # Forms
            # -------------------------
            forms = soup.find_all(
                "form"
            )

            result[
                "forms_count"
            ] = len(forms)

            # -------------------------
            # Buttons
            # -------------------------
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
                                "element": (
                                    "button"
                                ),
                            }
                        )

                        break

            # -------------------------
            # Remove duplicate CTAs
            # -------------------------
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

                seen.add(
                    key
                )

                unique_ctas.append(
                    cta
                )

            result["ctas"] = (
                unique_ctas
            )

            result["cta_count"] = (
                len(unique_ctas)
            )

            result["success"] = True

            await context.close()
            context = None

            await browser.close()
            browser = None

    except UnsafeURLError as exc:
        result["error"] = (
            f"Unsafe URL blocked: {exc}"
        )

    except Exception as exc:
        result["error"] = str(exc)

    finally:
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