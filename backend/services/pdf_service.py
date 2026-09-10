from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Optional

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


# =================================
# PATHS
# =================================

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"
PDF_DIR = REPORTS_DIR / "pdf"

PDF_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =================================
# BRAND COLORS
# =================================

BACKGROUND = HexColor("#07110F")
CARD = HexColor("#0D1916")
CARD_ALT = HexColor("#101F1B")
GREEN = HexColor("#42E3A4")
GREEN_DARK = HexColor("#123C30")
TEXT = HexColor("#F4F7F6")
MUTED = HexColor("#91A09B")
BORDER = HexColor("#24332F")

YELLOW = HexColor("#FFD479")
RED = HexColor("#FF9D9D")
BLUE = HexColor("#87BFFF")


# =================================
# HELPERS
# =================================

def _safe_text(
    value,
    fallback: str = "N/A",
) -> str:
    """
    Convert values into ReportLab-safe text.

    Groq and web content can contain Unicode punctuation that
    Helvetica does not render reliably. Normalize those characters
    to ASCII and HTML-escape the final value before using it inside
    a ReportLab Paragraph.
    """

    if value is None:
        return escape(
            fallback
        )

    text = str(
        value
    )

    replacements = {
        # Dashes / hyphens
        "\u2010": "-",   # hyphen
        "\u2011": "-",   # non-breaking hyphen
        "\u2012": "-",   # figure dash
        "\u2013": "-",   # en dash
        "\u2014": "-",   # em dash
        "\u2015": "-",   # horizontal bar
        "\u2212": "-",   # minus sign
        "\u00ad": "",    # soft hyphen

        # Quotes
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',

        # Bullets / spacing
        "\u2022": "-",
        "\u2023": "-",
        "\u2043": "-",
        "\u00a0": " ",
        "\u202f": " ",
        "\u2007": " ",

        # Ellipsis
        "\u2026": "...",
    }

    for old, new in replacements.items():
        text = text.replace(
            old,
            new,
        )

    # Remove other zero-width formatting characters that can
    # occasionally arrive from copied web/LLM text.
    for invisible in (
        "\u200b",
        "\u200c",
        "\u200d",
        "\ufeff",
    ):
        text = text.replace(
            invisible,
            "",
        )

    return escape(
        text
    )


def _format_score(
    score,
) -> str:
    if score is None:
        return "Unavailable"

    return f"{score}/100"


def _format_load_time(
    milliseconds,
) -> str:
    if milliseconds is None:
        return "N/A"

    try:
        return f"{float(milliseconds) / 1000:.2f}s"

    except (
        TypeError,
        ValueError,
    ):
        return "N/A"


def _severity_color(
    severity: str,
):
    severity = (
        severity
        or "low"
    ).lower()

    if severity in {
        "critical",
        "high",
    }:
        return RED

    if severity == "medium":
        return YELLOW

    return BLUE


def _severity_label(
    severity: str,
) -> str:
    return _safe_text(
        severity or "low"
    ).upper()


# =================================
# PAGE DECORATION
# =================================

def _draw_page(
    canvas,
    doc,
):
    canvas.saveState()

    width, height = A4

    # Background
    canvas.setFillColor(
        BACKGROUND
    )

    canvas.rect(
        0,
        0,
        width,
        height,
        fill=1,
        stroke=0,
    )

    # Header line
    canvas.setStrokeColor(
        BORDER
    )

    canvas.setLineWidth(
        0.5
    )

    canvas.line(
        18 * mm,
        height - 18 * mm,
        width - 18 * mm,
        height - 18 * mm,
    )

    # Logo mark
    canvas.setFillColor(
        GREEN
    )

    canvas.roundRect(
        18 * mm,
        height - 14.5 * mm,
        7 * mm,
        7 * mm,
        2 * mm,
        fill=1,
        stroke=0,
    )

    canvas.setFillColor(
        BACKGROUND
    )

    canvas.setFont(
        "Helvetica-Bold",
        7,
    )

    canvas.drawCentredString(
        21.5 * mm,
        height - 12.3 * mm,
        "L",
    )

    # Brand name
    canvas.setFillColor(
        TEXT
    )

    canvas.setFont(
        "Helvetica-Bold",
        10,
    )

    canvas.drawString(
        28 * mm,
        height - 12.7 * mm,
        "Leak",
    )

    canvas.setFillColor(
        GREEN
    )

    canvas.drawString(
        38 * mm,
        height - 12.7 * mm,
        "Lens",
    )

    # Footer
    canvas.setStrokeColor(
        BORDER
    )

    canvas.line(
        18 * mm,
        16 * mm,
        width - 18 * mm,
        16 * mm,
    )

    canvas.setFillColor(
        MUTED
    )

    canvas.setFont(
        "Helvetica",
        7.5,
    )

    canvas.drawString(
        18 * mm,
        10 * mm,
        "LeakLens Website Revenue Leak Report",
    )

    canvas.drawRightString(
        width - 18 * mm,
        10 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# =================================
# DOCUMENT CLASS
# =================================

class LeakLensDocTemplate(
    BaseDocTemplate
):
    def __init__(
        self,
        filename,
        **kwargs,
    ):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=25 * mm,
            bottomMargin=22 * mm,
            **kwargs,
        )

        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="normal",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )

        template = PageTemplate(
            id="leaklens",
            frames=[
                frame
            ],
            onPage=_draw_page,
        )

        self.addPageTemplates(
            [
                template
            ]
        )


# =================================
# STYLES
# =================================

def _build_styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="LLTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=27,
            leading=32,
            textColor=TEXT,
            alignment=TA_LEFT,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="LLSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=MUTED,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="LLSectionLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=GREEN,
            spaceBefore=8,
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="LLHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=23,
            textColor=TEXT,
            spaceBefore=3,
            spaceAfter=12,
        )
    )

    styles.add(
        ParagraphStyle(
            name="LLCardHeading",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=TEXT,
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="LLBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=14,
            textColor=MUTED,
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="LLBodyStrong",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=14,
            textColor=TEXT,
            spaceAfter=4,
        )
    )

    styles.add(
        ParagraphStyle(
            name="LLSmall",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=11,
            textColor=MUTED,
        )
    )

    styles.add(
        ParagraphStyle(
            name="LLScore",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=32,
            textColor=TEXT,
            alignment=TA_CENTER,
        )
    )

    styles.add(
        ParagraphStyle(
            name="LLScoreLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=MUTED,
            alignment=TA_CENTER,
        )
    )

    return styles


# =================================
# TABLE BUILDERS
# =================================

def _score_card(
    label: str,
    value: str,
    styles,
):
    content = [
        [
            Paragraph(
                _safe_text(label),
                styles["LLScoreLabel"],
            )
        ],
        [
            Paragraph(
                _safe_text(value),
                styles["LLScore"],
            )
        ],
    ]

    table = Table(
        content,
        colWidths=[
            42 * mm
        ],
        rowHeights=[
            10 * mm,
            18 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    CARD,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    BORDER,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    return table


def _metric_card(
    label: str,
    value: str,
    styles,
):
    table = Table(
        [
            [
                Paragraph(
                    _safe_text(label),
                    styles["LLSmall"],
                )
            ],
            [
                Paragraph(
                    f"<b>{_safe_text(value)}</b>",
                    styles["LLCardHeading"],
                )
            ],
        ],
        colWidths=[
            42 * mm
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    CARD,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    BORDER,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    return table


# =================================
# SECTION HELPERS
# =================================

def _section_heading(
    label: str,
    heading: str,
    styles,
):
    return [
        Paragraph(
            _safe_text(
                label
            ).upper(),
            styles[
                "LLSectionLabel"
            ],
        ),
        Paragraph(
            _safe_text(
                heading
            ),
            styles[
                "LLHeading"
            ],
        ),
    ]


def _issue_card(
    issue: dict,
    index: int,
    styles,
):
    severity = _severity_label(
        issue.get(
            "severity"
        )
    )

    severity_color = _severity_color(
        issue.get(
            "severity"
        )
    )

    title = (
        issue.get("message")
        or issue.get("title")
        or "Website issue"
    )

    body = [
        [
            Paragraph(
                f"<b>{index}</b>",
                styles["LLCardHeading"],
            ),
            Paragraph(
                _safe_text(title),
                styles["LLCardHeading"],
            ),
            Paragraph(
                f"<font color='{severity_color.hexval()}'>"
                f"<b>{severity}</b>"
                f"</font>",
                styles["LLSmall"],
            ),
        ]
    ]

    details = []

    category = issue.get(
        "category"
    )

    if category:
        details.append(
            f"<b>Category:</b> "
            f"{_safe_text(category).upper()}"
        )

    business_impact = issue.get(
        "business_impact"
    )

    if business_impact:
        details.append(
            f"<b>Why it matters:</b> "
            f"{_safe_text(business_impact)}"
        )

    recommendation = issue.get(
        "recommendation"
    )

    if recommendation:
        details.append(
            f"<b>Recommended fix:</b> "
            f"{_safe_text(recommendation)}"
        )

    body.append(
        [
            "",
            Paragraph(
                "<br/>".join(
                    details
                ),
                styles["LLBody"],
            ),
            "",
        ]
    )

    table = Table(
        body,
        colWidths=[
            11 * mm,
            137 * mm,
            25 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    CARD,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    BORDER,
                ),
                (
                    "SPAN",
                    (1, 1),
                    (2, 1),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    return table


# =================================
# PDF GENERATION
# =================================

def generate_pdf_report(
    report_id: str,
    report: dict,
) -> str:
    """
    Generate a branded LeakLens PDF report.

    Returns the absolute file path of the generated PDF.
    """

    output_path = (
        PDF_DIR
        / f"{report_id}.pdf"
    )

    styles = _build_styles()

    doc = LeakLensDocTemplate(
        str(
            output_path
        ),
        title=(
            "LeakLens Revenue Leak Report"
        ),
        author="LeakLens",
        subject=(
            "Website SEO, conversion, and "
            "performance audit"
        ),
    )

    story = []

    website = report.get(
        "website",
        {},
    )

    seo = report.get(
        "seo",
        {},
    )

    conversion = report.get(
        "conversion",
        {},
    )

    performance = report.get(
        "performance",
        {},
    )

    revenue = report.get(
        "revenue_leak",
        {},
    )

    ai = report.get(
        "ai_analysis"
    ) or {}

    category_scores = revenue.get(
        "category_scores",
        {},
    )

    # =================================
    # COVER / SUMMARY
    # =================================

    story.append(
        Spacer(
            1,
            8 * mm,
        )
    )

    story.append(
        Paragraph(
            "FULL REVENUE LEAK REPORT",
            styles[
                "LLSectionLabel"
            ],
        )
    )

    story.append(
        Paragraph(
            "LeakLens Website Audit",
            styles[
                "LLTitle"
            ],
        )
    )

    final_url = (
        website.get(
            "final_url"
        )
        or website.get(
            "url"
        )
        or "Unknown website"
    )

    story.append(
        Paragraph(
            _safe_text(
                final_url
            ),
            styles[
                "LLSubtitle"
            ],
        )
    )

    generated_at = (
        datetime.now(
            timezone.utc
        )
        .strftime(
            "%B %d, %Y"
        )
    )

    story.append(
        Paragraph(
            f"Report generated {generated_at}",
            styles[
                "LLSmall"
            ],
        )
    )

    story.append(
        Spacer(
            1,
            8 * mm,
        )
    )

    score_table = Table(
        [
            [
                _score_card(
                    "Revenue Leak Score",
                    f"{_safe_text(revenue.get('leak_score'))}/100",
                    styles,
                ),
                _score_card(
                    "SEO",
                    _format_score(
                        category_scores.get(
                            "seo"
                        )
                    ),
                    styles,
                ),
                _score_card(
                    "Conversion",
                    _format_score(
                        category_scores.get(
                            "conversion"
                        )
                    ),
                    styles,
                ),
                _score_card(
                    "Performance",
                    _format_score(
                        category_scores.get(
                            "performance"
                        )
                    ),
                    styles,
                ),
            ]
        ],
        colWidths=[
            43.25 * mm,
            43.25 * mm,
            43.25 * mm,
            43.25 * mm,
        ],
    )

    score_table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
            ]
        )
    )

    story.append(
        score_table
    )

    story.append(
        Spacer(
            1,
            5 * mm,
        )
    )

    metrics = Table(
        [
            [
                _metric_card(
                    "Risk Level",
                    revenue.get(
                        "risk_level",
                        "N/A",
                    ),
                    styles,
                ),
                _metric_card(
                    "Total Issues",
                    revenue.get(
                        "total_issues",
                        0,
                    ),
                    styles,
                ),
                _metric_card(
                    "Page Load",
                    _format_load_time(
                        performance.get(
                            "load_time_ms"
                        )
                    ),
                    styles,
                ),
                _metric_card(
                    "Requests",
                    performance.get(
                        "requests_count"
                    ),
                    styles,
                ),
            ]
        ],
        colWidths=[
            43.25 * mm,
            43.25 * mm,
            43.25 * mm,
            43.25 * mm,
        ],
    )

    metrics.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
            ]
        )
    )

    story.append(
        metrics
    )

    story.append(
        Spacer(
            1,
            8 * mm,
        )
    )

    disclaimer = Table(
        [
            [
                Paragraph(
                    (
                        "<b>Important:</b> "
                        "The Revenue Leak Score is a diagnostic "
                        "website friction index. It is not an "
                        "estimate of revenue percentage lost."
                    ),
                    styles[
                        "LLBody"
                    ],
                )
            ]
        ],
        colWidths=[
            173 * mm
        ],
    )

    disclaimer.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    GREEN_DARK,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    GREEN,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
            ]
        )
    )

    story.append(
        disclaimer
    )

    # =================================
    # EXECUTIVE SUMMARY
    # =================================

    executive_summary = ai.get(
        "executive_summary"
    )

    if executive_summary:
        story.append(
            Spacer(
                1,
                10 * mm,
            )
        )

        summary_table = Table(
            [
                [
                    Paragraph(
                        "AI EXECUTIVE SUMMARY",
                        styles[
                            "LLSectionLabel"
                        ],
                    )
                ],
                [
                    Paragraph(
                        "What this scan means for the business",
                        styles[
                            "LLHeading"
                        ],
                    )
                ],
                [
                    Paragraph(
                        _safe_text(
                            executive_summary
                        ),
                        styles[
                            "LLBody"
                        ],
                    )
                ],
            ],
            colWidths=[
                173 * mm
            ],
        )

        summary_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 2),
                        (-1, 2),
                        CARD_ALT,
                    ),
                    (
                        "BOX",
                        (0, 2),
                        (-1, 2),
                        0.7,
                        GREEN,
                    ),
                    (
                        "LEFTPADDING",
                        (0, 2),
                        (-1, 2),
                        12,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 2),
                        (-1, 2),
                        12,
                    ),
                    (
                        "TOPPADDING",
                        (0, 2),
                        (-1, 2),
                        12,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 2),
                        (-1, 2),
                        12,
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, 1),
                        0,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, 1),
                        0,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, 1),
                        0,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, 1),
                        0,
                    ),
                ]
            )
        )

        story.append(
            KeepTogether(
                [
                    summary_table
                ]
            )
        )

    # =================================
    # BUSINESS RISKS
    # =================================

    business_risks = ai.get(
        "business_risks",
        [],
    )

    if business_risks:
        story.append(
            PageBreak()
        )

        story.extend(
            _section_heading(
                "Business Risks",
                "Where the website may be losing opportunities",
                styles,
            )
        )

        for index, risk in enumerate(
            business_risks,
            start=1,
        ):
            severity = (
                risk.get(
                    "severity",
                    "low",
                )
            )

            severity_color = (
                _severity_color(
                    severity
                )
            )

            card = Table(
                [
                    [
                        Paragraph(
                            f"<b>{index:02}</b>",
                            styles[
                                "LLCardHeading"
                            ],
                        ),
                        Paragraph(
                            _safe_text(
                                risk.get(
                                    "title",
                                    "Business risk",
                                )
                            ),
                            styles[
                                "LLCardHeading"
                            ],
                        ),
                        Paragraph(
                            (
                                f"<font color='"
                                f"{severity_color.hexval()}"
                                f"'><b>"
                                f"{_severity_label(severity)}"
                                f"</b></font>"
                            ),
                            styles[
                                "LLSmall"
                            ],
                        ),
                    ],
                    [
                        "",
                        Paragraph(
                            (
                                f"{_safe_text(risk.get('explanation'))}"
                                f"<br/><br/>"
                                f"<b>Business impact:</b> "
                                f"{_safe_text(risk.get('business_impact'))}"
                            ),
                            styles[
                                "LLBody"
                            ],
                        ),
                        "",
                    ],
                ],
                colWidths=[
                    12 * mm,
                    136 * mm,
                    25 * mm,
                ],
            )

            card.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, -1),
                            CARD,
                        ),
                        (
                            "BOX",
                            (0, 0),
                            (-1, -1),
                            0.5,
                            BORDER,
                        ),
                        (
                            "SPAN",
                            (1, 1),
                            (2, 1),
                        ),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "TOP",
                        ),
                        (
                            "LEFTPADDING",
                            (0, 0),
                            (-1, -1),
                            8,
                        ),
                        (
                            "RIGHTPADDING",
                            (0, 0),
                            (-1, -1),
                            8,
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            8,
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            8,
                        ),
                    ]
                )
            )

            story.append(
                KeepTogether(
                    [
                        card,
                        Spacer(
                            1,
                            3 * mm,
                        ),
                    ]
                )
            )

    # =================================
    # PRIORITIZED FIXES
    # =================================

    prioritized_fixes = ai.get(
        "prioritized_fixes",
        [],
    )

    if prioritized_fixes:
        story.append(
            PageBreak()
        )

        story.extend(
            _section_heading(
                "Prioritized Action Plan",
                "Fix these first",
                styles,
            )
        )

        for fix in prioritized_fixes:
            priority = fix.get(
                "priority",
                "-",
            )

            severity = fix.get(
                "severity",
                "low",
            )

            severity_color = (
                _severity_color(
                    severity
                )
            )

            card = Table(
                [
                    [
                        Paragraph(
                            f"<b>#{priority}</b>",
                            styles[
                                "LLCardHeading"
                            ],
                        ),
                        Paragraph(
                            _safe_text(
                                fix.get(
                                    "title",
                                    "Recommended fix",
                                )
                            ),
                            styles[
                                "LLCardHeading"
                            ],
                        ),
                        Paragraph(
                            (
                                f"<font color='"
                                f"{severity_color.hexval()}"
                                f"'><b>"
                                f"{_severity_label(severity)}"
                                f"</b></font>"
                            ),
                            styles[
                                "LLSmall"
                            ],
                        ),
                    ],
                    [
                        "",
                        Paragraph(
                            (
                                f"<b>Category:</b> "
                                f"{_safe_text(fix.get('category')).upper()}"
                                f"<br/>"
                                f"<b>Why it matters:</b> "
                                f"{_safe_text(fix.get('why_it_matters'))}"
                                f"<br/>"
                                f"<b>Recommended action:</b> "
                                f"{_safe_text(fix.get('recommended_action'))}"
                            ),
                            styles[
                                "LLBody"
                            ],
                        ),
                        "",
                    ],
                ],
                colWidths=[
                    16 * mm,
                    132 * mm,
                    25 * mm,
                ],
            )

            card.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, -1),
                            CARD,
                        ),
                        (
                            "BOX",
                            (0, 0),
                            (-1, -1),
                            0.5,
                            BORDER,
                        ),
                        (
                            "SPAN",
                            (1, 1),
                            (2, 1),
                        ),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "TOP",
                        ),
                        (
                            "LEFTPADDING",
                            (0, 0),
                            (-1, -1),
                            8,
                        ),
                        (
                            "RIGHTPADDING",
                            (0, 0),
                            (-1, -1),
                            8,
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            8,
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            8,
                        ),
                    ]
                )
            )

            story.append(
                KeepTogether(
                    [
                        card,
                        Spacer(
                            1,
                            3 * mm,
                        ),
                    ]
                )
            )

    # =================================
    # QUICK WINS + 30-DAY PLAN
    # =================================

    quick_wins = ai.get(
        "quick_wins",
        [],
    )

    thirty_day_plan = ai.get(
        "thirty_day_plan",
        [],
    )

    if quick_wins or thirty_day_plan:
        # Start this combined execution page cleanly so the
        # QUICK WINS label can never be orphaned at the bottom
        # of the prioritized-fixes page.
        story.append(
            PageBreak()
        )

    if quick_wins:
        quick_section = []

        quick_section.extend(
            _section_heading(
                "Quick Wins",
                "High-value improvements you can start now",
                styles,
            )
        )

        quick_cells = []

        for win in quick_wins:
            quick_cells.append(
                Paragraph(
                    (
                        f"<b>{_safe_text(win.get('title'))}</b>"
                        f"<br/><br/>"
                        f"{_safe_text(win.get('action'))}"
                        f"<br/><br/>"
                        f"<b>Expected benefit:</b><br/>"
                        f"{_safe_text(win.get('expected_benefit'))}"
                    ),
                    styles[
                        "LLBody"
                    ],
                )
            )

        quick_table = Table(
            [
                quick_cells
            ],
            colWidths=[
                (173 / max(1, len(quick_cells))) * mm
                for _ in quick_cells
            ],
        )

        quick_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        CARD,
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        BORDER,
                    ),
                    (
                        "INNERGRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        BORDER,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        9,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        9,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        9,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        9,
                    ),
                ]
            )
        )

        quick_section.append(
            quick_table
        )

        story.append(
            KeepTogether(
                quick_section
            )
        )

    if thirty_day_plan:
        story.append(
            Spacer(
                1,
                9 * mm,
            )
        )

        plan_section = []

        plan_section.extend(
            _section_heading(
                "30-Day Improvement Plan",
                "A practical month-long roadmap",
                styles,
            )
        )

        plan_cells = []

        for week in thirty_day_plan:
            actions = week.get(
                "actions",
                [],
            )

            action_text = ""

            for action in actions:
                action_text += (
                    f"- {_safe_text(action)}<br/>"
                )

            plan_cells.append(
                Paragraph(
                    (
                        f"<font color='{GREEN.hexval()}'>"
                        f"<b>{_safe_text(week.get('period')).upper()}</b>"
                        f"</font>"
                        f"<br/><br/>"
                        f"<b>{_safe_text(week.get('focus'))}</b>"
                        f"<br/><br/>"
                        f"{action_text}"
                    ),
                    styles[
                        "LLBody"
                    ],
                )
            )

        plan_table = Table(
            [
                plan_cells
            ],
            colWidths=[
                (173 / max(1, len(plan_cells))) * mm
                for _ in plan_cells
            ],
        )

        plan_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        CARD,
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        BORDER,
                    ),
                    (
                        "INNERGRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        BORDER,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        10,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        10,
                    ),
                ]
            )
        )

        plan_section.append(
            plan_table
        )

        # Keeping the roadmap heading and table together prevents a
        # heading-only page break. If it cannot fit under Quick Wins,
        # ReportLab moves the whole roadmap cleanly to the next page.
        story.append(
            KeepTogether(
                plan_section
            )
        )

    # =================================
    # TECHNICAL FINDINGS
    # =================================

    all_issues = (
        seo.get(
            "issues",
            [],
        )
        + conversion.get(
            "issues",
            [],
        )
        + performance.get(
            "issues",
            [],
        )
    )

    severity_order = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
    }

    all_issues = sorted(
        all_issues,
        key=lambda issue: severity_order.get(
            issue.get(
                "severity",
                "low",
            ),
            0,
        ),
        reverse=True,
    )

    if all_issues:
        story.append(
            PageBreak()
        )

        story.extend(
            _section_heading(
                "Complete Analysis",
                "All detected website issues",
                styles,
            )
        )

        for index, issue in enumerate(
            all_issues,
            start=1,
        ):
            story.append(
                KeepTogether(
                    [
                        _issue_card(
                            issue,
                            index,
                            styles,
                        ),
                        Spacer(
                            1,
                            3 * mm,
                        ),
                    ]
                )
            )

    # =================================
    # FINAL NOTES
    # =================================

    story.append(
        Spacer(
            1,
            10 * mm,
        )
    )

    story.append(
        Paragraph(
            "ABOUT THIS REPORT",
            styles[
                "LLSectionLabel"
            ],
        )
    )

    story.append(
        Paragraph(
            (
                "LeakLens analyzes visible website signals across "
                "SEO, conversion pathways, and browser-measured "
                "performance. Findings are diagnostic and should "
                "be reviewed alongside analytics, customer data, "
                "and business context before major changes are made."
            ),
            styles[
                "LLBody"
            ],
        )
    )

    # =================================
    # BUILD PDF
    # =================================

    doc.build(
        story
    )

    return str(
        output_path.resolve()
    )


# =================================
# GET EXISTING PDF
# =================================

def get_pdf_path(
    report_id: str,
) -> Optional[str]:
    """
    Return an existing generated PDF path.
    """

    path = (
        PDF_DIR
        / f"{report_id}.pdf"
    )

    if not path.exists():
        return None

    return str(
        path.resolve()
    )
