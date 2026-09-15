"""Command-line interface for enterprise-doc-assistant."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Sequence


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agent_tools import DocumentAgent, DocumentIndexer, IndexingResult
from src.config import Settings, get_settings
from src.document_parser import DocumentParseError
from src.evaluator import EvaluationError, RetrievalEvaluator
from src.llm_client import LLMClientError
from src.vector_store import ChromaVectorStore, VectorStoreError


logger = logging.getLogger(__name__)


def _configure_console() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="enterprise-doc-assistant",
        description="企业文档智能助手 CLI（GLM-4.7-Flash + 本地 BGE + ChromaDB）",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    subparsers = parser.add_subparsers(dest="command")

    ingest = subparsers.add_parser("ingest", help="上传并索引 PDF/DOCX/MD/TXT")
    ingest.add_argument("paths", nargs="+", help="文件或目录路径")
    ingest.add_argument(
        "--no-recursive",
        action="store_true",
        help="目录模式不递归子目录",
    )
    ingest.add_argument(
        "--reset",
        action="store_true",
        help="索引前清空现有知识库",
    )

    chat = subparsers.add_parser("chat", help="启动多轮对话")
    chat.add_argument(
        "--show-tools",
        action="store_true",
        help="显示工具调用轨迹",
    )

    ask = subparsers.add_parser("ask", help="执行一次问答")
    ask.add_argument("question", help="问题文本")
    ask.add_argument(
        "--show-tools",
        action="store_true",
        help="显示工具调用轨迹",
    )

    subparsers.add_parser("documents", help="列出已索引文档")

    delete = subparsers.add_parser("delete", help="按 doc_id 删除文档")
    delete.add_argument("doc_id", help="文档 ID")

    evaluate = subparsers.add_parser("evaluate", help="运行离线 Top-K 检索评测")
    evaluate.add_argument(
        "--dataset",
        default="test_dataset/test_qa.csv",
        help="CSV 数据集路径",
    )
    evaluate.add_argument("--top-k", type=int, default=5, help="Top-K")
    evaluate.add_argument(
        "--output",
        default="",
        help="XLSX 输出路径；为空时写入 data/evaluations",
    )

    subparsers.add_parser("config", help="显示脱敏配置")
    return parser


def _build_services(
    settings: Settings,
) -> tuple[ChromaVectorStore, DocumentIndexer, DocumentAgent]:
    vector_store = ChromaVectorStore(settings)
    indexer = DocumentIndexer(settings, vector_store)
    agent = DocumentAgent(settings, vector_store=vector_store)
    return vector_store, indexer, agent


def _print_index_results(results: list[Any]) -> int:
    success_count = 0
    for result in results:
        if result.success:
            success_count += 1
            print(
                f"[成功] {result.source} | {result.chunks} 个分块 | "
                f"doc_id={result.doc_id}"
            )
        else:
            print(f"[失败] {result.source} | {result.message}")

    print(
        f"\n处理完成：成功 {success_count}，失败 {len(results) - success_count}。"
    )
    return 0 if success_count == len(results) else 1


def _command_ingest(args: argparse.Namespace, settings: Settings) -> int:
    vector_store, indexer, _ = _build_services(settings)
    if args.reset:
        vector_store.reset()
        print("知识库已清空。")

    results: list[Any] = []
    for raw_path in args.paths:
        path = Path(raw_path).expanduser()
        if path.is_dir():
            try:
                results.extend(
                    indexer.index_directory(
                        path,
                        recursive=not args.no_recursive,
                    )
                )
            except DocumentParseError as exc:
                print(f"[失败] {path} | {exc}")
                results.append(
                    IndexingResult(
                        source=str(path),
                        success=False,
                        message=str(exc),
                    )
                )
        else:
            results.extend(indexer.index_paths([path]))

    if not results:
        print("未发现可处理的 PDF/DOCX/MD/TXT 文件。")
        return 1
    return _print_index_results(results)


def _print_agent_response(response: Any, *, show_tools: bool) -> None:
    print("\n助手：")
    print(response.answer)
    if response.sources:
        print("\n来源：")
        seen: set[str] = set()
        for source in response.sources:
            label = source.get("filename") or source.get("source") or source.get(
                "doc_id", ""
            )
            if label and label not in seen:
                print(f"- {label}")
                seen.add(label)
    if show_tools and response.tool_calls:
        print("\n工具轨迹：")
        for record in response.tool_calls:
            print(
                f"- {record.get('name')} | {record.get('status')} | "
                f"{record.get('arguments', {})}"
            )
    if response.report_path:
        print(f"\n报告：{response.report_path}")


def _command_ask(args: argparse.Namespace, settings: Settings) -> int:
    _, _, agent = _build_services(settings)
    response = agent.run(args.question)
    _print_agent_response(response, show_tools=args.show_tools)
    return 0


def _command_chat(args: argparse.Namespace, settings: Settings) -> int:
    _, _, agent = _build_services(settings)
    print("=" * 68)
    print("enterprise-doc-assistant | 输入 /exit 退出，/clear 清空会话记忆")
    print("=" * 68)

    while True:
        try:
            question = input("\n你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n会话已结束。")
            return 0

        if not question:
            continue
        if question.lower() in {"/exit", "exit", "quit"}:
            print("会话已结束。")
            return 0
        if question.lower() == "/clear":
            agent.clear_memory()
            print("会话记忆已清空。")
            continue

        try:
            response = agent.run(question)
            _print_agent_response(response, show_tools=args.show_tools)
        except (LLMClientError, VectorStoreError, ValueError) as exc:
            print(f"\n[错误] {exc}")


def _command_documents(settings: Settings) -> int:
    vector_store = ChromaVectorStore(settings)
    try:
        documents = vector_store.list_documents()
        total_chunks = vector_store.count()
    except VectorStoreError as exc:
        print(f"[错误] {exc}")
        return 1

    if not documents:
        print("知识库为空。")
        return 0

    print(f"文档数：{len(documents)}，总向量分块数：{total_chunks}\n")
    print(f"{'文件名':<30} {'分块':>6}  doc_id")
    print("-" * 72)
    for document in documents:
        filename = str(document.get("filename", ""))[:28]
        print(
            f"{filename:<30} {int(document.get('chunks', 0)):>6}  "
            f"{document.get('doc_id', '')}"
        )
    return 0


def _command_delete(args: argparse.Namespace, settings: Settings) -> int:
    vector_store = ChromaVectorStore(settings)
    try:
        vector_store.delete_document(args.doc_id)
    except VectorStoreError as exc:
        print(f"[错误] {exc}")
        return 1
    print(f"已删除 doc_id={args.doc_id} 的文档分块。")
    return 0


def _command_evaluate(args: argparse.Namespace, settings: Settings) -> int:
    vector_store = ChromaVectorStore(settings)
    evaluator = RetrievalEvaluator(settings, vector_store)
    output = args.output or str(evaluator.default_output_path())
    result = evaluator.evaluate(
        args.dataset,
        top_k=args.top_k,
        output_path=output,
    )
    print(result.summary_text())
    print("\n问题明细：")
    print(
        result.details[
            ["序号", "问题", "期望来源", "是否命中", "首次命中排名", "错误"]
        ].to_string(index=False)
    )
    print(f"\n评测表格：{result.output_path}")
    return 0


def _command_config(settings: Settings) -> int:
    for key, value in settings.safe_summary().items():
        print(f"{key}: {value}")
    print(f"chunk_size: {settings.chunk_size}")
    print(f"chunk_overlap: {settings.chunk_overlap}")
    print(f"max_history_messages: {settings.max_history_messages}")
    print(f"max_context_chars: {settings.max_context_chars}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    _configure_console()
    parser = _build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    if not args.command:
        parser.print_help()
        return 0

    settings = get_settings()
    try:
        if args.command == "ingest":
            return _command_ingest(args, settings)
        if args.command == "ask":
            return _command_ask(args, settings)
        if args.command == "chat":
            return _command_chat(args, settings)
        if args.command == "documents":
            return _command_documents(settings)
        if args.command == "delete":
            return _command_delete(args, settings)
        if args.command == "evaluate":
            return _command_evaluate(args, settings)
        if args.command == "config":
            return _command_config(settings)
    except (DocumentParseError, EvaluationError, LLMClientError, VectorStoreError) as exc:
        print(f"\n[错误] {exc}")
        return 1
    except KeyboardInterrupt:
        print("\n操作已取消。")
        return 130
    except Exception as exc:
        logger.exception("Unhandled CLI error")
        print(f"\n[未预期错误] {exc}")
        return 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
