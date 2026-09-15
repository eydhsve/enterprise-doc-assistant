"""Gradio web interface for enterprise-doc-assistant."""

from __future__ import annotations

import logging
import shutil
import sys
import threading
import uuid
from pathlib import Path
from typing import Any, Sequence


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gradio as gr

from src.agent_tools import DocumentAgent, DocumentIndexer
from src.config import Settings, get_settings
from src.document_parser import DocumentParser
from src.evaluator import RetrievalEvaluator
from src.llm_client import LLMClientError, ZhipuLLMClient
from src.vector_store import ChromaVectorStore, VectorStoreError


logger = logging.getLogger(__name__)

_SERVICES_LOCK = threading.RLock()
_SERVICES: "WebServices | None" = None


class WebServices:
    """Lazily initialized shared application services."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.vector_store = ChromaVectorStore(settings)
        self.llm_client = ZhipuLLMClient(settings)
        self.indexer = DocumentIndexer(settings, self.vector_store)
        self.agent = DocumentAgent(
            settings,
            llm_client=self.llm_client,
            vector_store=self.vector_store,
        )
        self.evaluator = RetrievalEvaluator(settings, self.vector_store)


def get_services() -> WebServices:
    global _SERVICES
    with _SERVICES_LOCK:
        if _SERVICES is None:
            _SERVICES = WebServices(get_settings())
        return _SERVICES


def _copy_uploads(paths: list[str] | tuple[str, ...] | None) -> list[Path]:
    if not paths:
        return []

    services = get_services()
    upload_dir = services.settings.upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []

    for raw_path in paths:
        source = Path(raw_path).expanduser()
        if not source.is_file():
            continue
        safe_name = source.name.replace(" ", "_")
        target = upload_dir / f"{uuid.uuid4().hex[:8]}_{safe_name}"
        try:
            shutil.copy2(source, target)
            copied.append(target)
        except OSError as exc:
            logger.warning("Upload copy failed for %s: %s", source, exc)
    return copied


def _format_documents(documents: list[dict[str, Any]]) -> str:
    if not documents:
        return "知识库暂无已索引文档。"

    lines = [
        "| 文件名 | 类型 | 分块数 | doc_id |",
        "|---|---:|---:|---|",
    ]
    for document in documents[:100]:
        filename = str(document.get("filename", "")).replace("|", "\\|")
        extension = str(document.get("extension", "")).replace("|", "\\|")
        chunks = int(document.get("chunks", 0))
        doc_id = str(document.get("doc_id", ""))
        lines.append(
            f"| {filename} | {extension} | {chunks} | `{doc_id}` |"
        )
    if len(documents) > 100:
        lines.append(f"| 其余 {len(documents) - 100} 个文档已省略 |  |  |  |")
    return "\n".join(lines)


def _knowledge_state() -> str:
    services = get_services()
    try:
        count = services.vector_store.count()
        documents = services.vector_store.list_documents()
        return (
            f"**知识库状态**：{len(documents)} 个文档，"
            f"{count} 个向量分块"
        )
    except VectorStoreError as exc:
        return f"**知识库状态**：初始化失败，{exc}"


def initial_status() -> str:
    services = get_services()
    summary = services.settings.safe_summary()
    api_state = (
        "已配置" if summary["api_key_configured"] else "未配置 ZHIPU_API_KEY"
    )
    return (
        f"**模型**：`{summary['model']}`（{api_state}）  \n"
        f"**嵌入模型**：`{summary['embedding_model']}`  \n"
        f"**ChromaDB**：`{summary['chroma_dir']}`  \n"
        f"**检索 Top-K**：{summary['retrieval_top_k']}"
    )


def health_handler() -> str:
    services = get_services()
    lines = [initial_status()]
    try:
        count = services.vector_store.count()
        lines.append(f"**知识库**：{count} 个向量分块")
    except VectorStoreError as exc:
        lines.append(f"**知识库异常**：{exc}")

    healthy, message = services.llm_client.health_check()
    lines.append(
        f"**GLM 连通性**：{'正常' if healthy else '失败'}  \n`{message}`"
    )
    return "\n\n".join(lines)


def ingest_handler(
    files: list[str] | tuple[str, ...] | None,
    chunk_size: int,
    chunk_overlap: int,
    reset_first: bool,
    progress: gr.Progress = gr.Progress(),
) -> tuple[str, str, str]:
    services = get_services()
    if not files:
        return "请选择 PDF、DOCX、MD 或 TXT 文件。", _format_documents([]), _knowledge_state()

    if int(chunk_overlap) >= int(chunk_size):
        return (
            "分块重叠必须小于分块大小。",
            _format_documents(services.vector_store.list_documents()),
            _knowledge_state(),
        )

    try:
        if reset_first:
            progress(0.05, desc="正在清空知识库")
            services.vector_store.reset()

        copied = _copy_uploads(files)
        if not copied:
            return "上传文件复制失败，请检查磁盘权限。", _format_documents([]), _knowledge_state()

        parser = DocumentParser(
            chunk_size=int(chunk_size),
            chunk_overlap=int(chunk_overlap),
        )
        indexer = DocumentIndexer(
            services.settings,
            services.vector_store,
            parser=parser,
        )

        progress(0.15, desc="正在解析并向量化")
        results = indexer.index_paths(copied)
        succeeded = [item for item in results if item.success]
        failed = [item for item in results if not item.success]
        total_chunks = sum(item.chunks for item in succeeded)

        status_lines = [
            (
                f"**索引完成**：成功 {len(succeeded)} 个，失败 "
                f"{len(failed)} 个，新增/更新 {total_chunks} 个分块。"
            )
        ]
        for item in failed:
            status_lines.append(
                f"- `{Path(item.source).name}`：{item.message}"
            )

        documents = services.vector_store.list_documents()
        progress(1.0, desc="完成")
        return (
            "\n".join(status_lines),
            _format_documents(documents),
            _knowledge_state(),
        )
    except (ValueError, VectorStoreError, OSError) as exc:
        return f"索引失败：{exc}", _format_documents([]), _knowledge_state()
    except Exception as exc:
        logger.exception("Unexpected web ingestion error")
        return f"索引失败：{exc}", _format_documents([]), _knowledge_state()


def refresh_documents_handler() -> tuple[str, str]:
    services = get_services()
    try:
        documents = services.vector_store.list_documents()
        return _format_documents(documents), _knowledge_state()
    except VectorStoreError as exc:
        return f"读取文档列表失败：{exc}", f"**知识库状态**：{exc}"


def clear_knowledge_handler() -> tuple[str, str, str]:
    services = get_services()
    try:
        services.vector_store.reset()
        return "知识库已清空。", _format_documents([]), _knowledge_state()
    except VectorStoreError as exc:
        return f"清空失败：{exc}", _format_documents([]), _knowledge_state()


def chat_handler(
    message: str,
    history: list[dict[str, Any]] | None,
) -> tuple[str, list[dict[str, Any]], str]:
    history = list(history or [])
    question = (message or "").strip()
    if not question:
        return "", history, _knowledge_state()

    history.append({"role": "user", "content": question})
    services = get_services()

    try:
        response = services.agent.run(question)
        answer = response.answer
        if response.sources:
            source_names: list[str] = []
            seen: set[str] = set()
            for source in response.sources:
                label = (
                    source.get("filename")
                    or source.get("source")
                    or source.get("doc_id", "")
                )
                if label and label not in seen:
                    source_names.append(label)
                    seen.add(label)
            if source_names:
                answer += "\n\n**引用来源**  \n" + "  \n".join(
                    f"- {name}" for name in source_names
                )
        if response.report_path:
            answer += f"\n\n**报告文件**：`{response.report_path}`"
        history.append({"role": "assistant", "content": answer})
        status = _knowledge_state()
    except (LLMClientError, VectorStoreError, ValueError) as exc:
        history.append({"role": "assistant", "content": f"请求失败：{exc}"})
        status = f"**请求失败**：{exc}"
    except Exception as exc:
        logger.exception("Unexpected web chat error")
        history.append(
            {
                "role": "assistant",
                "content": f"系统发生未预期错误：{exc}",
            }
        )
        status = f"**系统异常**：{exc}"

    return "", history, status


def clear_chat_handler() -> tuple[list[Any], str]:
    get_services().agent.clear_memory()
    return [], "会话记忆已清空。"


def build_demo(settings: Settings | None = None) -> gr.Blocks:
    """Build the complete Gradio application."""

    global _SERVICES
    if settings is not None:
        with _SERVICES_LOCK:
            _SERVICES = WebServices(settings)

    services = get_services()
    initial_documents = _format_documents(
        services.vector_store.list_documents()
    )
    theme = gr.themes.Soft(
        primary_hue=gr.themes.colors.teal,
        secondary_hue=gr.themes.colors.blue,
        neutral_hue=gr.themes.colors.gray,
        font=[
            "Segoe UI",
            "Microsoft YaHei",
            "sans-serif",
        ],
    )

    css = """
    :root {
      --ink: #17212b;
      --muted: #5d6b78;
      --line: #d8dee5;
      --accent: #0f766e;
      --accent-soft: #e7f4f2;
      --surface: #f7f8fa;
    }
    .gradio-container {
      max-width: 1440px !important;
      background: #ffffff !important;
      color: var(--ink);
    }
    .app-header {
      border-bottom: 1px solid var(--line);
      padding: 14px 2px 12px;
      margin-bottom: 12px;
    }
    .app-title {
      font-size: 25px !important;
      font-weight: 700 !important;
      letter-spacing: 0 !important;
      margin: 0 !important;
    }
    .app-subtitle {
      color: var(--muted) !important;
      margin-top: 3px !important;
    }
    .panel {
      border: 1px solid var(--line) !important;
      border-radius: 8px !important;
      padding: 12px !important;
      background: #ffffff !important;
    }
    .status-box {
      background: var(--surface) !important;
      border-left: 3px solid var(--accent) !important;
      border-radius: 4px !important;
      padding: 10px 12px !important;
    }
    .send-button {
      min-width: 96px !important;
    }
    .chatbot {
      border: 1px solid var(--line) !important;
      border-radius: 8px !important;
    }
    footer { display: none !important; }
    """

    with gr.Blocks(
        title="企业文档智能助手",
        theme=theme,
        css=css,
        fill_height=True,
    ) as demo:
        with gr.Row(elem_classes=["app-header"]):
            with gr.Column(scale=8):
                gr.Markdown(
                    "# 企业文档智能助手",
                    elem_classes=["app-title"],
                )
                gr.Markdown(
                    "私有知识库问答 · GLM-4.7-Flash · 本地 BGE · ChromaDB",
                    elem_classes=["app-subtitle"],
                )
            with gr.Column(scale=3, min_width=260):
                status = gr.Markdown(
                    initial_status(),
                    elem_classes=["status-box"],
                )

        with gr.Row(equal_height=False):
            with gr.Column(scale=5, min_width=360):
                with gr.Group(elem_classes=["panel"]):
                    gr.Markdown("### 文档管理")
                    upload = gr.File(
                        label="文档",
                        file_count="multiple",
                        file_types=[".pdf", ".docx", ".md", ".txt"],
                        type="filepath",
                    )
                    with gr.Accordion("分块参数", open=False):
                        chunk_size = gr.Slider(
                            minimum=200,
                            maximum=1500,
                            value=services.settings.chunk_size,
                            step=50,
                            label="分块大小（字符）",
                        )
                        chunk_overlap = gr.Slider(
                            minimum=0,
                            maximum=500,
                            value=min(
                                services.settings.chunk_overlap,
                                500,
                            ),
                            step=25,
                            label="重叠字符数",
                        )
                        reset_first = gr.Checkbox(
                            value=False,
                            label="索引前清空知识库",
                        )
                    with gr.Row():
                        ingest_button = gr.Button(
                            "建立索引",
                            variant="primary",
                        )
                        refresh_button = gr.Button("刷新列表")
                    ingest_status = gr.Markdown(
                        "尚未执行索引。",
                        elem_classes=["status-box"],
                    )
                    knowledge_status = gr.Markdown(_knowledge_state())
                    document_table = gr.Markdown(initial_documents)
                    clear_knowledge_button = gr.Button(
                        "清空知识库",
                        variant="stop",
                    )

            with gr.Column(scale=7, min_width=460):
                with gr.Group(elem_classes=["panel"]):
                    gr.Markdown("### 知识问答")
                    chatbot = gr.Chatbot(
                        value=[],
                        type="messages",
                        label="对话",
                        height=590,
                        elem_classes=["chatbot"],
                    )
                    with gr.Row():
                        message = gr.Textbox(
                            placeholder="输入问题",
                            label="",
                            lines=1,
                            max_lines=6,
                            scale=8,
                            autofocus=True,
                        )
                        send_button = gr.Button(
                            "发送",
                            variant="primary",
                            elem_classes=["send-button"],
                            scale=1,
                        )
                    with gr.Row():
                        clear_chat_button = gr.Button("清空会话")
                        health_button = gr.Button("检查连接")

        ingest_button.click(
            fn=ingest_handler,
            inputs=[
                upload,
                chunk_size,
                chunk_overlap,
                reset_first,
            ],
            outputs=[ingest_status, document_table, knowledge_status],
            show_progress="full",
        )
        refresh_button.click(
            fn=refresh_documents_handler,
            inputs=[],
            outputs=[document_table, knowledge_status],
        )
        clear_knowledge_button.click(
            fn=clear_knowledge_handler,
            inputs=[],
            outputs=[
                ingest_status,
                document_table,
                knowledge_status,
            ],
        )
        send_button.click(
            fn=chat_handler,
            inputs=[message, chatbot],
            outputs=[message, chatbot, status],
        )
        message.submit(
            fn=chat_handler,
            inputs=[message, chatbot],
            outputs=[message, chatbot, status],
        )
        clear_chat_button.click(
            fn=clear_chat_handler,
            inputs=[],
            outputs=[chatbot, status],
        )
        health_button.click(
            fn=health_handler,
            inputs=[],
            outputs=[status],
        )

    return demo


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    settings = get_settings()
    demo = build_demo(settings)
    demo.queue(default_concurrency_limit=4).launch(
        server_name=settings.gradio_server_name,
        server_port=settings.gradio_server_port,
        share=settings.gradio_share,
        show_error=True,
        inbrowser=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
