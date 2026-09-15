"""Function-calling tools, document indexing, and the enterprise agent."""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .config import Settings
from .conversation_mem import ConversationMemory
from .document_parser import (
    DocumentParseError,
    DocumentParser,
    ParsedDocument,
)
from .llm_client import LLMClientError, ZhipuLLMClient
from .vector_store import ChromaVectorStore, SearchHit, VectorStoreError


logger = logging.getLogger(__name__)


class AgentToolError(RuntimeError):
    """Raised when a tool cannot complete its operation."""


@dataclass(frozen=True)
class ToolResult:
    """Normalized output returned by a function-calling tool."""

    content: str
    sources: list[dict[str, str]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IndexingResult:
    """Result of indexing one source document."""

    source: str
    success: bool
    chunks: int = 0
    doc_id: str = ""
    message: str = ""


@dataclass(frozen=True)
class AgentResponse:
    """Final answer and execution trace."""

    answer: str
    sources: list[dict[str, str]]
    tool_calls: list[dict[str, Any]]
    report_path: str | None = None


class DocumentIndexer:
    """Parse documents and persist chunks in the local vector store."""

    def __init__(
        self,
        settings: Settings,
        vector_store: ChromaVectorStore,
        parser: DocumentParser | None = None,
    ) -> None:
        self.settings = settings
        self.vector_store = vector_store
        self.parser = parser or DocumentParser(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

    def index_paths(self, paths: Iterable[str | Path]) -> list[IndexingResult]:
        """Index explicit files. Each file fails independently."""

        results: list[IndexingResult] = []
        for item in paths:
            path = Path(item).expanduser()
            if not path.exists():
                results.append(
                    IndexingResult(
                        source=str(path),
                        success=False,
                        message="文件不存在。",
                    )
                )
                continue
            try:
                document = self.parser.parse_file(path)
                results.append(self._index_document(document))
            except (DocumentParseError, VectorStoreError, OSError) as exc:
                logger.warning("Indexing failed for %s: %s", path, exc)
                results.append(
                    IndexingResult(
                        source=str(path),
                        success=False,
                        message=str(exc),
                    )
                )
        return results

    def index_directory(
        self,
        directory: str | Path,
        *,
        recursive: bool = True,
    ) -> list[IndexingResult]:
        """Collect supported files from a directory and index them."""

        files = self.parser.collect_files(directory, recursive=recursive)
        return self.index_paths(files)

    def _index_document(self, document: ParsedDocument) -> IndexingResult:
        if not document.chunks:
            return IndexingResult(
                source=document.path,
                success=False,
                doc_id=document.doc_id,
                message="未生成有效文本分块。",
            )

        old_doc_id = self.vector_store.find_document_id(document.path)
        if old_doc_id and old_doc_id != document.doc_id:
            self.vector_store.delete_document(old_doc_id)

        chunk_count = self.vector_store.add_chunks(
            doc_id=document.doc_id,
            source=document.path,
            chunks=document.chunks,
            document=document,
        )
        return IndexingResult(
            source=document.path,
            success=True,
            chunks=chunk_count,
            doc_id=document.doc_id,
            message="索引完成。",
        )


class KnowledgeRetrieveTool:
    """Retrieve private knowledge from ChromaDB."""

    definition: dict[str, Any] = {
        "type": "function",
        "function": {
            "name": "knowledge_retrieve",
            "description": (
                "检索企业私有知识库。回答制度、流程、产品、项目或文档事实问题时，"
                "必须优先调用本工具。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "用于语义检索的问题或关键词，应保留关键实体。",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回的候选片段数量，默认使用系统配置。",
                        "minimum": 1,
                        "maximum": 10,
                    },
                    "source_filter": {
                        "type": "string",
                        "description": "可选，按文件名或路径片段过滤来源。",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    }

    def __init__(
        self,
        vector_store: ChromaVectorStore,
        default_top_k: int = 4,
    ) -> None:
        self.vector_store = vector_store
        self.default_top_k = default_top_k

    def run(
        self,
        *,
        query: str,
        top_k: int | None = None,
        source_filter: str | None = None,
    ) -> ToolResult:
        normalized_query = (query or "").strip()
        if not normalized_query:
            raise AgentToolError("knowledge_retrieve 缺少有效 query。")

        requested_k = int(top_k or self.default_top_k)
        requested_k = max(1, min(10, requested_k))
        try:
            hits = self.vector_store.search(
                normalized_query,
                top_k=requested_k,
                source_filter=source_filter,
            )
        except VectorStoreError as exc:
            raise AgentToolError(str(exc)) from exc

        if not hits:
            return ToolResult(
                content=(
                    "知识库未检索到相关内容。请提示用户先上传并索引文档，"
                    "或将问题改写为更具体的关键词。"
                ),
                metadata={"query": normalized_query, "hit_count": 0},
            )

        context_parts: list[str] = []
        sources: list[dict[str, str]] = []
        context_items: list[dict[str, Any]] = []

        for rank, hit in enumerate(hits, start=1):
            source = str(hit.metadata.get("source", "未知来源"))
            filename = str(hit.metadata.get("filename", Path(source).name))
            chunk_index = str(hit.metadata.get("chunk_index", ""))
            score = round(hit.score, 4)
            context_parts.append(
                f"[片段 {rank} | 来源: {filename} | 分块: {chunk_index} | "
                f"相似度: {score}]\n{hit.text}"
            )
            sources.append(
                {
                    "doc_id": str(hit.metadata.get("doc_id", "")),
                    "source": source,
                    "filename": filename,
                }
            )
            context_items.append(
                {
                    "rank": rank,
                    "text": hit.text,
                    "score": score,
                    "metadata": hit.metadata,
                }
            )

        return ToolResult(
            content="\n\n".join(context_parts),
            sources=sources,
            metadata={
                "query": normalized_query,
                "hit_count": len(hits),
                "context_items": context_items,
            },
        )


class DocSummaryTool:
    """Summarize one indexed document through GLM-4.7-Flash."""

    definition: dict[str, Any] = {
        "type": "function",
        "function": {
            "name": "doc_summary",
            "description": (
                "对知识库中某一篇已索引文档生成结构化摘要。"
                "用户要求总结整篇文档时调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "文档 ID，可从 knowledge_retrieve 的来源中获取。",
                    },
                    "source": {
                        "type": "string",
                        "description": "也可传文件名或路径片段，由工具查找文档。",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "最多送入摘要模型的原文字符数。",
                        "minimum": 1000,
                        "maximum": 30000,
                    },
                },
                "additionalProperties": False,
            },
        },
    }

    def __init__(
        self,
        vector_store: ChromaVectorStore,
        llm_client: ZhipuLLMClient,
    ) -> None:
        self.vector_store = vector_store
        self.llm_client = llm_client

    def run(
        self,
        *,
        doc_id: str | None = None,
        source: str | None = None,
        max_chars: int = 12000,
    ) -> ToolResult:
        resolved_doc_id = (doc_id or "").strip()
        if not resolved_doc_id and source:
            resolved_doc_id = self.vector_store.find_document_id(source) or ""
        if not resolved_doc_id:
            raise AgentToolError(
                "未找到目标文档。请先调用 knowledge_retrieve，"
                "或传入正确的 doc_id/source。"
            )

        try:
            chunks = self.vector_store.get_document_chunks(resolved_doc_id)
        except VectorStoreError as exc:
            raise AgentToolError(str(exc)) from exc
        if not chunks:
            raise AgentToolError(f"文档 {resolved_doc_id} 没有可摘要内容。")

        limit = max(1000, min(30000, int(max_chars or 12000)))
        content_parts: list[str] = []
        used_chars = 0
        source_label = ""
        filename = ""

        for hit in chunks:
            if used_chars >= limit:
                break
            remaining = limit - used_chars
            text = hit.text[:remaining]
            content_parts.append(text)
            used_chars += len(text)
            source_label = source_label or str(hit.metadata.get("source", ""))
            filename = filename or str(hit.metadata.get("filename", ""))

        try:
            summary = self.llm_client.summarize(
                "\n\n".join(content_parts),
                instruction=(
                    f"请总结文档《{filename or resolved_doc_id}》。"
                    "摘要要覆盖文档目的、核心内容、关键结论和待办风险。"
                ),
                max_chars=limit,
            )
        except LLMClientError as exc:
            raise AgentToolError(f"文档摘要模型调用失败: {exc}") from exc

        source_item = {
            "doc_id": resolved_doc_id,
            "source": source_label,
            "filename": filename or Path(source_label).name,
        }
        return ToolResult(
            content=summary,
            sources=[source_item],
            metadata={
                "doc_id": resolved_doc_id,
                "characters_used": used_chars,
                "chunk_count": len(chunks),
            },
        )


class ExportReportTool:
    """Write a Q&A result to a local Markdown report."""

    definition: dict[str, Any] = {
        "type": "function",
        "function": {
            "name": "export_report",
            "description": (
                "将当前问答结论、依据和来源导出为本地 Markdown 报告。"
                "当用户明确要求保存、导出或生成报告时调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "用户原始问题。",
                    },
                    "answer": {
                        "type": "string",
                        "description": "准备写入报告的完整回答。",
                    },
                    "sources": {
                        "type": "array",
                        "description": "回答所依据的来源名称或路径。",
                        "items": {"type": "string"},
                    },
                    "report_name": {
                        "type": "string",
                        "description": "报告文件名前缀，可选。",
                    },
                },
                "required": ["question", "answer"],
                "additionalProperties": False,
            },
        },
    }

    def __init__(self, report_dir: str | Path) -> None:
        self.report_dir = Path(report_dir).expanduser().resolve()
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def run(
        self,
        *,
        question: str,
        answer: str,
        sources: list[str] | str | None = None,
        report_name: str | None = None,
    ) -> ToolResult:
        question_text = (question or "").strip()
        answer_text = (answer or "").strip()
        if not question_text or not answer_text:
            raise AgentToolError("export_report 需要 question 和 answer。")

        source_list = self._normalize_sources(sources)
        stem = self._safe_stem(report_name or "enterprise_qa_report")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{stem}_{timestamp}_{uuid.uuid4().hex[:6]}.md"
        report_path = (self.report_dir / filename).resolve()

        if self.report_dir not in report_path.parents:
            raise AgentToolError("报告路径越界，已拒绝写入。")

        source_lines = (
            "\n".join(f"- {item}" for item in source_list)
            if source_list
            else "- 未提供来源"
        )
        content = (
            "# 企业文档智能助手问答报告\n\n"
            f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- 报告主题：{question_text}\n\n"
            "## 问题\n\n"
            f"{question_text}\n\n"
            "## 回答\n\n"
            f"{answer_text}\n\n"
            "## 依据来源\n\n"
            f"{source_lines}\n"
        )

        try:
            with self._lock:
                report_path.write_text(content, encoding="utf-8")
        except OSError as exc:
            raise AgentToolError(f"报告写入失败: {exc}") from exc

        return ToolResult(
            content=f"报告已导出到: {report_path}",
            metadata={"report_path": str(report_path)},
        )

    @staticmethod
    def _normalize_sources(sources: list[str] | str | None) -> list[str]:
        if sources is None:
            return []
        if isinstance(sources, str):
            return [
                item.strip()
                for item in re.split(r"[\n,;]+", sources)
                if item.strip()
            ]
        return [str(item).strip() for item in sources if str(item).strip()]

    @staticmethod
    def _safe_stem(value: str) -> str:
        stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value).strip(" ._")
        stem = stem[:60]
        return stem or "enterprise_qa_report"


class DocumentAgent:
    """GLM-4.7-Flash agent with complete function-calling execution."""

    SYSTEM_PROMPT = """你是 enterprise-doc-assistant 企业文档智能助手。
你的职责是基于企业私有知识库进行准确问答、文档摘要和报告导出。

工具使用规则：
1. 涉及企业制度、流程、产品、项目、文档事实时，必须先调用 knowledge_retrieve。
2. 用户要求总结整篇文档时，优先调用 doc_summary。
3. 用户明确要求保存、导出或生成 Markdown 报告时，调用 export_report。
4. 每次工具调用后，根据工具结果继续推理；必要时可连续调用多个工具。
5. 最终回答只依据工具返回内容和用户明确提供的信息，不得编造来源。
6. 检索为空时要明确说明知识库未检索到依据，并给出可执行的补充建议。
7. 回答使用清晰中文，先给结论，再给依据和必要注意事项，并列出引用文件名。
"""

    def __init__(
        self,
        settings: Settings,
        *,
        llm_client: ZhipuLLMClient | None = None,
        vector_store: ChromaVectorStore | None = None,
        memory: ConversationMemory | None = None,
        max_tool_rounds: int = 6,
    ) -> None:
        self.settings = settings
        self.llm_client = llm_client or ZhipuLLMClient(settings)
        self.vector_store = vector_store or ChromaVectorStore(settings)
        self.memory = memory or ConversationMemory(
            max_messages=settings.max_history_messages,
            max_context_chars=settings.max_context_chars,
        )
        self.max_tool_rounds = max(1, max_tool_rounds)

        self.knowledge_tool = KnowledgeRetrieveTool(
            self.vector_store,
            default_top_k=settings.retrieval_top_k,
        )
        self.summary_tool = DocSummaryTool(
            self.vector_store,
            self.llm_client,
        )
        self.export_tool = ExportReportTool(settings.report_dir)
        self.tool_definitions = [
            self.knowledge_tool.definition,
            self.summary_tool.definition,
            self.export_tool.definition,
        ]

    def run(self, question: str) -> AgentResponse:
        """Run one user turn through the tool-calling loop."""

        question_text = (question or "").strip()
        if not question_text:
            raise ValueError("问题不能为空。")

        messages = self.memory.context_messages(
            self.SYSTEM_PROMPT,
            current_user_message=question_text,
        )
        source_items: list[dict[str, str]] = []
        tool_records: list[dict[str, Any]] = []
        assistant_content = ""

        for round_index in range(self.max_tool_rounds):
            response = self.llm_client.chat_completion(
                messages,
                tools=self.tool_definitions,
                tool_choice="auto",
            )
            tool_calls = response.get("tool_calls") or []
            assistant_content = str(response.get("content") or "").strip()

            if not tool_calls:
                break

            assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": assistant_content or None,
                "tool_calls": tool_calls,
            }
            messages.append(assistant_message)

            for tool_call in tool_calls:
                function = tool_call.get("function") or {}
                tool_name = str(function.get("name", ""))
                tool_call_id = str(tool_call.get("id") or f"call_{uuid.uuid4().hex}")
                arguments, parse_error = self._parse_arguments(
                    function.get("arguments")
                )

                if parse_error:
                    result_content = json.dumps(
                        {"ok": False, "error": parse_error},
                        ensure_ascii=False,
                    )
                    tool_record = {
                        "name": tool_name,
                        "arguments": {},
                        "status": "error",
                        "error": parse_error,
                    }
                else:
                    (
                        result_content,
                        result_sources,
                        metadata,
                        tool_error,
                    ) = self._execute_tool(tool_name, arguments)
                    self._merge_sources(source_items, result_sources)
                    tool_record = {
                        "name": tool_name,
                        "arguments": arguments,
                        "status": "error" if tool_error else "success",
                        "metadata": metadata,
                    }
                    if tool_error:
                        tool_record["error"] = tool_error

                tool_records.append(tool_record)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result_content,
                    }
                )

            if round_index == self.max_tool_rounds - 1:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "工具调用轮次已达上限。请停止调用工具，"
                            "现在基于已有工具结果给出最终中文回答。"
                        ),
                    }
                )
                final_response = self.llm_client.chat_completion(
                    messages,
                    temperature=0.1,
                )
                assistant_content = str(
                    final_response.get("content") or ""
                ).strip()

        if not assistant_content:
            assistant_content = (
                "当前未能生成有效回答。请检查 GLM-4.7-Flash 配置和知识库状态后重试。"
            )

        report_path: str | None = None
        for record in tool_records:
            metadata = record.get("metadata") or {}
            if record.get("name") == "export_report" and metadata.get("report_path"):
                report_path = str(metadata["report_path"])

        self.memory.add_exchange(question_text, assistant_content)
        return AgentResponse(
            answer=assistant_content,
            sources=source_items,
            tool_calls=tool_records,
            report_path=report_path,
        )

    def _execute_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> tuple[str, list[dict[str, str]], dict[str, Any], str | None]:
        try:
            if name == "knowledge_retrieve":
                result = self.knowledge_tool.run(
                    query=str(arguments.get("query", "")),
                    top_k=arguments.get("top_k"),
                    source_filter=arguments.get("source_filter"),
                )
            elif name == "doc_summary":
                result = self.summary_tool.run(
                    doc_id=arguments.get("doc_id"),
                    source=arguments.get("source"),
                    max_chars=int(arguments.get("max_chars") or 12000),
                )
            elif name == "export_report":
                result = self.export_tool.run(
                    question=str(arguments.get("question", "")),
                    answer=str(arguments.get("answer", "")),
                    sources=arguments.get("sources"),
                    report_name=arguments.get("report_name"),
                )
            else:
                raise AgentToolError(f"未知工具: {name}")
        except (AgentToolError, ValueError, TypeError) as exc:
            logger.warning("Tool %s failed: %s", name, exc)
            payload = {
                "ok": False,
                "error": str(exc),
                "instruction": "请修正参数；无法修正时向用户说明原因。",
            }
            return (
                json.dumps(payload, ensure_ascii=False),
                [],
                {},
                str(exc),
            )
        except Exception as exc:
            logger.exception("Unexpected tool error: %s", name)
            message = f"工具 {name} 发生未预期错误: {exc}"
            return (
                json.dumps({"ok": False, "error": message}, ensure_ascii=False),
                [],
                {},
                message,
            )

        payload = {
            "ok": True,
            "result": result.content,
            "metadata": result.metadata,
        }
        return (
            json.dumps(payload, ensure_ascii=False, default=str),
            result.sources,
            result.metadata,
            None,
        )

    @staticmethod
    def _parse_arguments(raw: Any) -> tuple[dict[str, Any], str | None]:
        if isinstance(raw, dict):
            return raw, None
        if raw is None or raw == "":
            return {}, None
        try:
            parsed = json.loads(str(raw))
        except json.JSONDecodeError as exc:
            return {}, f"工具参数不是合法 JSON: {exc}"
        if not isinstance(parsed, dict):
            return {}, "工具参数必须是 JSON 对象。"
        return parsed, None

    @staticmethod
    def _merge_sources(
        target: list[dict[str, str]],
        incoming: list[dict[str, str]],
    ) -> None:
        seen = {
            (item.get("doc_id", ""), item.get("source", ""))
            for item in target
        }
        for item in incoming:
            key = (item.get("doc_id", ""), item.get("source", ""))
            if key not in seen:
                target.append(item)
                seen.add(key)

    def clear_memory(self) -> None:
        self.memory.clear()
