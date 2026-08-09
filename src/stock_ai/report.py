from __future__ import annotations

from typing import Any


def _text(value: Any, default: str = "暂无数据") -> str:
    if value is None or value == "":
        return default
    return str(value)


def _bullets(values: Any) -> list[str]:
    if not isinstance(values, list) or not values:
        return ["- 暂无数据"]
    return [f"- {_text(value)}" for value in values]


def _analysis_section(title: str, section: Any) -> list[str]:
    if not isinstance(section, dict):
        return [f"## {title}", "", "暂无数据", ""]
    lines = [
        f"## {title}",
        "",
        _text(section.get("conclusion")),
        "",
        "### 主要依据",
        "",
        *_bullets(section.get("evidence")),
        "",
        "### 主要风险",
        "",
        *_bullets(section.get("risks")),
        "",
    ]
    return lines


def render_markdown_report(report: dict[str, Any]) -> str:
    stock = report.get("stock", {})
    overall = report.get("overall", {})
    metadata = report.get("analysis_metadata", {})
    scorecard = report.get("scorecard", {})
    analysis = report.get("analysis", {})
    outlook = report.get("outlook", {})
    action_plan = report.get("action_plan", {})
    data_quality = report.get("data_quality", {})
    validation = report.get("validation", {})
    verified_facts = report.get("verified_facts", {})

    if not isinstance(stock, dict):
        stock = {}
    if not isinstance(overall, dict):
        overall = {}
    if not isinstance(metadata, dict):
        metadata = {}

    lines = [
        f"# {_text(stock.get('name'), '未知股票')}（{_text(stock.get('code'), '未知代码')}）AI投资研究报告",
        "",
        f"- 行业：{_text(stock.get('industry'))}",
        f"- 综合评分：{_text(overall.get('total_score'))}/100",
        f"- 研究结论：{_text(overall.get('rating'))}",
        f"- 置信度：{_text(overall.get('confidence'))}",
        f"- 分析模型：{_text(metadata.get('model'))}",
        f"- 生成时间：{_text(metadata.get('generated_at'))}",
        f"- 源数据时间：{_text(metadata.get('source_data_generated_at'))}",
        "",
        "## 综合结论",
        "",
        _text(overall.get("summary")),
        "",
        "## 程序校验",
        "",
    ]

    if isinstance(validation, dict):
        status_labels = {
            "passed": "通过",
            "corrected": "发现并自动修正",
            "warning": "存在警告",
        }
        lines.extend(
            [
                f"- 校验状态：{status_labels.get(validation.get('status'), _text(validation.get('status')))}",
                f"- 自动修正：{_text(validation.get('corrections_count'), '0')}处",
                f"- 数据警告：{_text(validation.get('warnings_count'), '0')}项",
                "",
            ]
        )

        market_position = (
            verified_facts.get("market_position", {})
            if isinstance(verified_facts, dict)
            else {}
        )
        if isinstance(market_position, dict) and market_position.get("summary"):
            lines.extend(
                [
                    "确定性行情事实：",
                    "",
                    f"- {_text(market_position.get('summary'))}",
                    "",
                ]
            )

        corrections = validation.get("corrections", [])
        if isinstance(corrections, list) and corrections:
            lines.extend(["自动修正记录：", ""])
            for correction in corrections:
                if not isinstance(correction, dict):
                    continue
                lines.append(
                    "- "
                    + _text(correction.get("path"), correction.get("code", "未知位置"))
                    + "："
                    + _text(correction.get("original"))
                    + " → "
                    + _text(correction.get("corrected"))
                )
            lines.append("")

        warnings = validation.get("warnings", [])
        if isinstance(warnings, list) and warnings:
            lines.extend(["校验警告：", ""])
            for warning in warnings:
                if isinstance(warning, dict):
                    lines.append(f"- {_text(warning.get('message'))}")
            lines.append("")

        lines.extend(
            [
                _text(
                    validation.get("note"),
                    "程序校验不能替代人工复核。",
                ),
                "",
            ]
        )
    else:
        lines.extend(["尚未执行程序校验。", ""])

    lines.extend(
        [
        "## 评分明细",
        "",
        "| 维度 | 得分 | 理由 |",
        "| --- | ---: | --- |",
        ]
    )

    score_labels = (
        ("fundamental", "基本面", 30),
        ("growth", "成长性", 20),
        ("valuation", "估值", 20),
        ("trend", "技术趋势", 15),
        ("risk_control", "风险控制", 15),
    )
    for key, label, maximum in score_labels:
        item = scorecard.get(key, {}) if isinstance(scorecard, dict) else {}
        if not isinstance(item, dict):
            item = {}
        reason = _text(item.get("reason")).replace("|", "｜").replace("\n", " ")
        lines.append(
            f"| {label} | {_text(item.get('score'))}/{maximum} | {reason} |"
        )
    lines.append("")

    for key, title in (
        ("fundamental", "基本面分析"),
        ("growth", "成长性分析"),
        ("valuation", "估值分析"),
        ("technical", "技术趋势分析"),
    ):
        section = analysis.get(key, {}) if isinstance(analysis, dict) else {}
        lines.extend(_analysis_section(title, section))

    event_section = (
        analysis.get("news_and_events", {})
        if isinstance(analysis, dict)
        else {}
    )
    if not isinstance(event_section, dict):
        event_section = {}
    lines.extend(
        [
            "## 新闻与事件",
            "",
            _text(event_section.get("conclusion")),
            "",
            "### 正面事件",
            "",
            *_bullets(event_section.get("positive_events")),
            "",
            "### 负面事件",
            "",
            *_bullets(event_section.get("negative_events")),
            "",
            "### 待确认事件",
            "",
            *_bullets(event_section.get("uncertain_events")),
            "",
        ]
    )

    lines.extend(["## 预期走势", ""])
    for key, title in (("short_term", "短期"), ("medium_term", "中期")):
        section = outlook.get(key, {}) if isinstance(outlook, dict) else {}
        if not isinstance(section, dict):
            section = {}
        lines.extend(
            [
                f"### {title}（{_text(section.get('horizon'))}）",
                "",
                f"判断：{_text(section.get('view'))}",
                "",
                "主要驱动：",
                "",
                *_bullets(section.get("drivers")),
                "",
                "判断失效条件：",
                "",
                *_bullets(section.get("invalidation_conditions")),
                "",
            ]
        )

    lines.extend(["### 情景分析", ""])
    scenarios = outlook.get("scenarios", []) if isinstance(outlook, dict) else []
    if not isinstance(scenarios, list) or not scenarios:
        lines.extend(["暂无数据", ""])
    else:
        for scenario in scenarios:
            if not isinstance(scenario, dict):
                continue
            lines.extend(
                [
                    f"#### {_text(scenario.get('name'))}情景",
                    "",
                    f"可能走势：{_text(scenario.get('expected_direction'))}",
                    "",
                    "发生条件：",
                    "",
                    *_bullets(scenario.get("conditions")),
                    "",
                    f"应对方式：{_text(scenario.get('response'))}",
                    "",
                ]
            )

    if not isinstance(action_plan, dict):
        action_plan = {}
    lines.extend(
        [
            "## 研究与风险计划",
            "",
            f"当前态度：{_text(action_plan.get('stance'))}",
            "",
            "适用研究偏好：",
            "",
            *_bullets(action_plan.get("suitable_for")),
            "",
            "后续跟踪指标：",
            "",
            *_bullets(action_plan.get("watch_indicators")),
            "",
            "仓位和风险纪律：",
            "",
            *_bullets(action_plan.get("position_and_risk_notes")),
            "",
        ]
    )

    if not isinstance(data_quality, dict):
        data_quality = {}
    lines.extend(
        [
            "## 数据质量",
            "",
            "可用数据：",
            "",
            *_bullets(data_quality.get("available_sections")),
            "",
            "缺失数据：",
            "",
            *_bullets(data_quality.get("missing_sections")),
            "",
            "分析限制：",
            "",
            *_bullets(data_quality.get("limitations")),
            "",
            "---",
            "",
            _text(
                report.get("disclaimer"),
                "本报告仅用于个人研究和项目演示，不构成投资建议。",
            ),
            "",
        ]
    )
    return "\n".join(lines)
