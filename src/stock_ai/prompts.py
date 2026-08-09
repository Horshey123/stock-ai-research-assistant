from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = """你是严谨的A股研究助理。你的任务是根据用户提供的数据生成结构化研究报告。

必须遵守：
1. 只能使用输入数据中的事实，不得虚构财务数字、实时价格、新闻或公司事件。
2. 明确区分“数据事实”和“分析推断”；数据缺失时写“未知”并降低置信度。
3. 投资价值从基本面、成长性、估值、技术趋势、事件与风险共同判断。
4. 走势只能做条件化情景分析，不得承诺收益，不得声称必涨或必跌。
5. 引用关键数字时写明指标、时间或数据区间。
6. 风险控制得分越高，代表风险相对越低、数据质量越好。
7. 输入数据中的verified_facts由程序确定性计算，优先级最高，任何文字不得与其矛盾。
8. 特别核对最新收盘价相对MA20、MA60、MA120的位置，不得把“高于”写成“低于”。
9. 最终只返回一个合法JSON对象，不要使用Markdown代码围栏，不要输出JSON之外的文字。
"""


OUTPUT_SCHEMA = {
    "report_version": "0.1.0",
    "stock": {
        "code": "股票代码",
        "name": "股票名称",
        "industry": "行业",
    },
    "overall": {
        "total_score": "0到100的整数",
        "rating": "积极关注/关注/观察/谨慎/暂不参与 五选一",
        "confidence": "高/中/低 三选一",
        "summary": "80到160字的综合结论",
    },
    "scorecard": {
        "fundamental": {
            "score": "0到30",
            "reason": "理由",
        },
        "growth": {
            "score": "0到20",
            "reason": "理由",
        },
        "valuation": {
            "score": "0到20",
            "reason": "理由",
        },
        "trend": {
            "score": "0到15",
            "reason": "理由",
        },
        "risk_control": {
            "score": "0到15",
            "reason": "理由",
        },
    },
    "analysis": {
        "fundamental": {
            "conclusion": "结论",
            "evidence": ["带数据和日期的证据"],
            "risks": ["风险"],
        },
        "growth": {
            "conclusion": "结论",
            "evidence": ["证据"],
            "risks": ["风险"],
        },
        "valuation": {
            "conclusion": "结论",
            "evidence": ["证据"],
            "risks": ["风险"],
        },
        "technical": {
            "conclusion": "结论",
            "evidence": ["证据"],
            "risks": ["风险"],
        },
        "news_and_events": {
            "conclusion": "结论",
            "positive_events": ["正面事件"],
            "negative_events": ["负面事件"],
            "uncertain_events": ["待确认事件"],
        },
    },
    "outlook": {
        "short_term": {
            "horizon": "未来1到3个月",
            "view": "偏强/震荡偏强/震荡/震荡偏弱/偏弱 五选一",
            "drivers": ["影响因素"],
            "invalidation_conditions": ["会使判断失效的条件"],
        },
        "medium_term": {
            "horizon": "未来6到12个月",
            "view": "偏强/震荡偏强/震荡/震荡偏弱/偏弱 五选一",
            "drivers": ["影响因素"],
            "invalidation_conditions": ["会使判断失效的条件"],
        },
        "scenarios": [
            {
                "name": "乐观/中性/悲观",
                "conditions": ["发生条件"],
                "expected_direction": "可能走势，不给出虚假精确目标价",
                "response": "观察或风险应对",
            }
        ],
    },
    "action_plan": {
        "stance": "积极关注/关注/观察/谨慎/暂不参与 五选一",
        "suitable_for": ["可能适合的研究偏好，不做个性化承诺"],
        "watch_indicators": ["后续需要跟踪的指标"],
        "position_and_risk_notes": ["非个性化的仓位与止损纪律提示"],
    },
    "data_quality": {
        "available_sections": ["可用数据"],
        "missing_sections": ["缺失或失败数据"],
        "limitations": ["因此产生的分析限制"],
    },
    "disclaimer": "本报告仅用于个人研究和项目演示，不构成投资建议。",
}


def build_analysis_messages(context: dict[str, Any]) -> list[dict[str, str]]:
    schema_text = json.dumps(OUTPUT_SCHEMA, ensure_ascii=False, indent=2)
    context_text = json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    user_prompt = f"""请分析下面的A股数据，并严格按照指定结构返回JSON。

评分规则：
- 基本面满分30分；
- 成长性满分20分；
- 估值满分20分；
- 技术趋势满分15分；
- 风险控制满分15分；
- total_score必须等于五项得分之和。

输出结构：
{schema_text}

输入数据：
{context_text}
"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
