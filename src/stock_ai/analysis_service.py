from __future__ import annotations

from datetime import datetime
from typing import Any

from stock_ai.analysis_payload import build_analysis_context
from stock_ai.deepseek_client import DeepSeekClient
from stock_ai.prompts import build_analysis_messages
from stock_ai.validation import build_verified_facts, validate_and_correct_report


class StockAnalysisService:
    """Prepare stock evidence and turn it into a structured AI report."""

    def __init__(self, client: DeepSeekClient | None = None):
        self.client = client or DeepSeekClient()

    @staticmethod
    def prepare_context(bundle: dict[str, Any]) -> dict[str, Any]:
        context = build_analysis_context(bundle)
        context["verified_facts"] = build_verified_facts(context)
        return context

    def analyze_context(self, context: dict[str, Any]) -> dict[str, Any]:
        messages = build_analysis_messages(context)
        model_report, usage = self.client.generate_analysis(messages)

        stock = context.get("stock", {})
        model_report["report_version"] = "0.1.0"
        model_report["stock"] = {
            "code": stock.get("code"),
            "name": stock.get("name"),
            "industry": stock.get("industry"),
        }
        model_report["analysis_metadata"] = {
            "generated_at": datetime.now().astimezone().isoformat(
                timespec="seconds"
            ),
            "model": self.client.model,
            "source_data_generated_at": context.get("data_generated_at"),
            "context_schema_version": context.get("context_schema_version"),
            "usage": usage,
        }
        model_report.setdefault(
            "disclaimer",
            "本报告仅用于个人研究和项目演示，不构成投资建议。",
        )
        return validate_and_correct_report(model_report, context)

    def analyze_bundle(
        self,
        bundle: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        context = self.prepare_context(bundle)
        return context, self.analyze_context(context)
