import argparse
import json
import sys
from pathlib import Path

from stock_ai.analysis_service import StockAnalysisService
from stock_ai.deepseek_client import DeepSeekClient
from stock_ai.exceptions import StockAIError
from stock_ai.report import render_markdown_report
from stock_ai.service import PROJECT_ROOT, StockDataService
from stock_ai.validation import validate_and_correct_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="使用 BaoStock + AKShare 生成AI可用的A股数据包。"
    )
    parser.add_argument("code", help="6位沪深A股代码，例如 600519")
    parser.add_argument("--years", type=int, default=3, help="历史数据年数，默认3")
    parser.add_argument("--notice-limit", type=int, default=20)
    parser.add_argument("--news-limit", type=int, default=20)
    parser.add_argument("--no-cache", action="store_true", help="忽略本地缓存")
    parser.add_argument("--skip-news", action="store_true", help="跳过新闻接口")
    parser.add_argument("--skip-reports", action="store_true", help="跳过三大财务报表")
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="调用DeepSeek并生成AI分析JSON和Markdown报告",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="只生成精简分析上下文，不调用DeepSeek",
    )
    parser.add_argument(
        "--validate-existing",
        action="store_true",
        help="离线校验已有的context和analysis，不调用DeepSeek",
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        help="读取已有股票JSON并跳过数据采集",
    )
    parser.add_argument(
        "--context-json",
        type=Path,
        help="已有分析上下文路径；用于--validate-existing",
    )
    parser.add_argument(
        "--analysis-json",
        type=Path,
        help="已有AI分析路径；用于--validate-existing",
    )
    parser.add_argument(
        "--base-url",
        help="DeepSeek兼容接口地址；默认读取DEEPSEEK_BASE_URL",
    )
    parser.add_argument(
        "--model",
        help="模型名称；默认读取DEEPSEEK_MODEL或使用deepseek-v4-pro",
    )
    parser.add_argument(
        "--ai-timeout",
        type=float,
        default=120,
        help="AI接口超时秒数，默认120",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="输出JSON路径；默认 data/output/<股票代码>.json",
    )
    return parser


def _read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as file:
            value = json.load(file)
    except FileNotFoundError as error:
        raise StockAIError(f"找不到输入文件：{path}") from error
    except json.JSONDecodeError as error:
        raise StockAIError(f"输入文件不是有效JSON：{path}") from error
    if not isinstance(value, dict):
        raise StockAIError("输入JSON的顶层必须是对象。")
    return value


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.input_json and not (args.analyze or args.prepare_only):
        parser.error("--input-json需要与--analyze或--prepare-only一起使用")
    if args.validate_existing and (args.analyze or args.prepare_only):
        parser.error("--validate-existing不能与--analyze或--prepare-only同时使用")
    if (args.context_json or args.analysis_json) and not args.validate_existing:
        parser.error("--context-json和--analysis-json需要与--validate-existing一起使用")

    output = args.output or PROJECT_ROOT / "data" / "output" / f"{args.code}.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    if args.validate_existing:
        context_path = (
            args.context_json
            or output.parent / f"{args.code}_context.json"
        ).resolve()
        analysis_path = (
            args.analysis_json
            or output.parent / f"{args.code}_analysis.json"
        ).resolve()
        try:
            context = _read_json(context_path)
            analysis = _read_json(analysis_path)
        except StockAIError as error:
            print(f"校验失败：{error}", file=sys.stderr)
            raise SystemExit(1) from error
        validated = validate_and_correct_report(analysis, context)
        validated_analysis_path = (
            analysis_path.parent / f"{args.code}_analysis_validated.json"
        )
        validated_report_path = (
            analysis_path.parent / f"{args.code}_report_validated.md"
        )
        _write_json(validated_analysis_path, validated)
        validated_report_path.write_text(
            render_markdown_report(validated),
            encoding="utf-8",
        )
        validation = validated.get("validation", {})
        print(f"已校验上下文：{context_path}")
        print(f"已校验AI分析：{analysis_path}")
        print(
            "校验结果："
            f"{validation.get('status', 'unknown')}，"
            f"修正{validation.get('corrections_count', 0)}处，"
            f"警告{validation.get('warnings_count', 0)}项"
        )
        print(f"已生成校验版分析：{validated_analysis_path}")
        print(f"已生成校验版报告：{validated_report_path}")
        return

    try:
        if args.input_json:
            data_path = args.input_json.resolve()
            bundle = _read_json(data_path)
            bundle_code = str(bundle.get("stock", {}).get("code", ""))
            if bundle_code and bundle_code != args.code:
                raise StockAIError(
                    f"输入文件股票代码为{bundle_code}，与命令中的{args.code}不一致。"
                )
        else:
            data_path = output.resolve()
            bundle = StockDataService().build_bundle(
                args.code,
                years=max(1, args.years),
                notice_limit=max(1, args.notice_limit),
                news_limit=max(1, args.news_limit),
                use_cache=not args.no_cache,
                include_news=not args.skip_news,
                include_reports=not args.skip_reports,
            )
            _write_json(data_path, bundle)
    except StockAIError as error:
        print(f"获取失败：{error}", file=sys.stderr)
        raise SystemExit(1) from error

    if not args.input_json:
        statuses = bundle.get("source_status", {})
        ok_sections = [
            key
            for key, status in statuses.items()
            if status.get("status") == "ok"
        ]
        failed_sections = [
            key
            for key, status in statuses.items()
            if status.get("status") == "error"
        ]
        print(f"已生成数据：{data_path}")
        print(f"成功模块：{', '.join(ok_sections) or '无'}")
        if failed_sections:
            print(f"降级模块：{', '.join(failed_sections)}")
    else:
        print(f"已读取数据：{data_path}")

    if args.analyze or args.prepare_only:
        artifact_directory = data_path.parent
        context_path = artifact_directory / f"{args.code}_context.json"
        analysis_path = artifact_directory / f"{args.code}_analysis.json"
        report_path = artifact_directory / f"{args.code}_report.md"
        client = DeepSeekClient(
            base_url=args.base_url,
            model=args.model,
            timeout=max(10, args.ai_timeout),
        )
        analysis_service = StockAnalysisService(client=client)
        context = analysis_service.prepare_context(bundle)
        _write_json(context_path, context)
        print(f"已生成分析上下文：{context_path}")

        if args.analyze:
            try:
                analysis = analysis_service.analyze_context(context)
            except StockAIError as error:
                print(f"AI分析失败：{error}", file=sys.stderr)
                raise SystemExit(1) from error
            _write_json(analysis_path, analysis)
            report_path.write_text(
                render_markdown_report(analysis),
                encoding="utf-8",
            )
            validation = analysis.get("validation", {})
            print(f"已生成AI分析：{analysis_path}")
            print(f"已生成可读报告：{report_path}")
            print(
                "程序校验："
                f"{validation.get('status', 'unknown')}，"
                f"修正{validation.get('corrections_count', 0)}处，"
                f"警告{validation.get('warnings_count', 0)}项"
            )


if __name__ == "__main__":
    main()
