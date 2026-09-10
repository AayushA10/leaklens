import json
import os

import httpx


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

DEFAULT_MODEL = "openai/gpt-oss-120b"


def _build_analysis_payload(full_report: dict) -> dict:
    """
    Reduce the full scanner report into the most useful information
    for the AI analysis.

    This keeps the prompt focused and avoids sending unnecessary data.
    """

    website = full_report.get("website", {})
    seo = full_report.get("seo", {})
    conversion = full_report.get("conversion", {})
    performance = full_report.get("performance", {})
    revenue_leak = full_report.get("revenue_leak", {})

    return {
        "website": {
            "url": website.get("url"),
            "final_url": website.get("final_url"),
            "title": website.get("title"),
        },

        "scores": {
            "health_score": revenue_leak.get("health_score"),
            "leak_score": revenue_leak.get("leak_score"),
            "risk_level": revenue_leak.get("risk_level"),
            "category_scores": revenue_leak.get("category_scores"),
        },

        "issue_counts": {
            "total": revenue_leak.get("total_issues"),
            "critical": revenue_leak.get("critical_issues"),
            "high": revenue_leak.get("high_issues"),
            "medium": revenue_leak.get("medium_issues"),
            "low": revenue_leak.get("low_issues"),
        },

        "seo": {
            "score": seo.get("score"),
            "issues": seo.get("issues", []),
        },

        "conversion": {
            "score": conversion.get("score"),
            "issues": conversion.get("issues", []),
        },

        "performance": {
            "status": performance.get("status"),
            "score": performance.get("score"),
            "load_time_ms": performance.get("load_time_ms"),
            "dom_content_loaded_ms": performance.get(
                "dom_content_loaded_ms"
            ),
            "page_size_kb": performance.get("page_size_kb"),
            "requests_count": performance.get("requests_count"),
            "issues": performance.get("issues", []),
        },
    }


async def generate_ai_analysis(
    full_report: dict,
) -> dict:
    """
    Generate an executive website analysis using Groq.

    Returns structured JSON containing:
    - executive summary
    - business risks
    - prioritized fixes
    - quick wins
    - 30-day action plan
    """

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return {
            "success": False,
            "error": "GROQ_API_KEY is not configured.",
            "analysis": None,
        }

    scan_data = _build_analysis_payload(
        full_report
    )

    system_prompt = """
You are a senior website optimization and digital growth consultant.

You are analyzing a technical website scan from a product called LeakLens.

Your job is to translate technical findings into clear business language.

Important rules:

1. Use only the evidence provided in the scan data.
2. Do not invent traffic numbers, revenue values, conversion rates,
   rankings, customer counts, or financial loss estimates.
3. Do not claim that a specific issue is definitely causing lost revenue.
   Use careful language such as "may", "can", "could", or
   "creates potential friction".
4. Prioritize critical and high-severity issues first.
5. Be specific and actionable.
6. Do not repeat the same recommendation in multiple sections.
7. If a category is unavailable, acknowledge that it was not measured.
8. Keep the tone professional and useful to a business owner.
9. Return valid JSON only.
10. Do not wrap the JSON in markdown code fences.

Return exactly this JSON structure:

{
  "executive_summary": "string",

  "business_risks": [
    {
      "title": "string",
      "severity": "critical | high | medium | low",
      "explanation": "string",
      "business_impact": "string"
    }
  ],

  "prioritized_fixes": [
    {
      "priority": 1,
      "title": "string",
      "category": "seo | conversion | performance",
      "severity": "critical | high | medium | low",
      "why_it_matters": "string",
      "recommended_action": "string"
    }
  ],

  "quick_wins": [
    {
      "title": "string",
      "action": "string",
      "expected_benefit": "string"
    }
  ],

  "thirty_day_plan": [
    {
      "period": "Week 1",
      "focus": "string",
      "actions": ["string"]
    },
    {
      "period": "Week 2",
      "focus": "string",
      "actions": ["string"]
    },
    {
      "period": "Week 3",
      "focus": "string",
      "actions": ["string"]
    },
    {
      "period": "Week 4",
      "focus": "string",
      "actions": ["string"]
    }
  ]
}
""".strip()

    user_prompt = (
        "Analyze the following LeakLens website scan.\n\n"
        + json.dumps(
            scan_data,
            indent=2,
        )
    )

    payload = {
        "model": DEFAULT_MODEL,

        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],

        "temperature": 0.2,

        "response_format": {
            "type": "json_object"
        },
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(
            timeout=60.0
        ) as client:
            response = await client.post(
                GROQ_API_URL,
                headers=headers,
                json=payload,
            )

        response.raise_for_status()

        response_data = response.json()

        content = (
            response_data
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        )

        if not content:
            return {
                "success": False,
                "error": (
                    "Groq returned an empty response."
                ),
                "analysis": None,
            }

        try:
            analysis = json.loads(
                content
            )

        except json.JSONDecodeError:
            return {
                "success": False,
                "error": (
                    "Groq returned invalid JSON."
                ),
                "analysis": None,
            }

        return {
            "success": True,
            "error": None,
            "analysis": analysis,
        }

    except httpx.HTTPStatusError as exc:
        error_message = (
            f"Groq API returned HTTP "
            f"{exc.response.status_code}."
        )

        try:
            error_body = exc.response.json()

            groq_message = (
                error_body
                .get("error", {})
                .get("message")
            )

            if groq_message:
                error_message = groq_message

        except Exception:
            pass

        return {
            "success": False,
            "error": error_message,
            "analysis": None,
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "analysis": None,
        }