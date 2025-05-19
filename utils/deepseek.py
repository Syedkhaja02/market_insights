"""Simple DeepSeek client used for AI recommendations."""
from __future__ import annotations
import os, requests
from typing import Dict, Any

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "YOUR_PLACEHOLDER_KEY")
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

SYS_PROMPT = (
    "You are a senior growth strategist. "
    "Given a KPI comparison table (JSON) for a brand and its competitors, "
    "return 3–5 concise, actionable recommendations in Markdown bullets. "
    "Be crisp, quantitative, and avoid generic advice."
)


class DeepSeekError(RuntimeError):
    """Raised when DeepSeek API returns an error."""


def fetch_insight(kpi_json: str, brand_name: str) -> str:
    """Return Markdown string with recommendations."""

    payload: Dict[str, Any] = {
        "model": "deepseek-chat",  # replace if you use a different engine
        "temperature": 0.7,
        "messages": [
            {"role": "system", "content": SYS_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Brand: {brand_name}\nKPI_Table_JSON:\n{kpi_json}\n"\
                    "Please reply with markdown bullet points only."
                ),
            },
        ],
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    resp = requests.post(DEEPSEEK_ENDPOINT, json=payload, timeout=30)
    if resp.status_code != 200:
        raise DeepSeekError(f"{resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # noqa: BLE001
        raise DeepSeekError("Malformed DeepSeek response") from exc