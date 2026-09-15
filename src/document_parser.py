"""Document parsing, cleaning, and overlapping chunking."""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}


class DocumentParseError(RuntimeError):
    """Raised when a document cannot be read or parsed."""


@dataclass(frozen=True)
class Chunk:
    """A text chunk and its source position."""

    text: str
    index: int
    start_char: int
    end_char: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self, document: "ParsedDocument") -> dict[str, Any]:
        metadata = {
            "doc_id": document.doc_id,
            "source": document.path,
            "filename": document.filename,
            "extension": document.extension,
            "title": document.title,
            "chunk_index": self.index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "modified_at": document.modified_at,
            "file_size": document.file_size,
        }
        metadata.update(self.metadata)
        return metadata


@dataclass(frozen=True)
class ParsedDocument:
    """A parsed document and all generated chunks."""

    doc_id: str
    path: str
    filename: str
    extension: str
    title: str
    text: str
    chunks: list[Chunk]
    modified_at: str
    file_size: int


class DocumentParser:
    """Parse supported file types and split them into overlapping chunks."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100) -> None:
        if chunk_size < 100:
            raise ValueError("chunk_size 不能小于 100。")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须大于等于 0 且小于 chunk_size。")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @staticmethod
    def is_supported(path: str | Path) -> bool:
        return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS

    def parse_file(self, path: str | Path) -> ParsedDocument:
        """Parse a file and return cleaned text with overlapping chunks."""

        file_path = Path(path).expanduser()
        try:
            file_path = file_path.resolve(strict=True)
        except FileNotFoundError as exc:
            raise DocumentParseError(f"文件不存在: {file_path}") from exc
        except OSError as exc:
            raise DocumentParseError(f"文件路径不可访问: {file_path}") from exc

        if not file_path.is_file():
            raise DocumentParseError(f"不是有效文件: {file_path}")

        extension = file_path.suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise DocumentParseError(
                f"不支持的文件类型 {extension or '<无扩展名>'}，"
                f"仅支持 {', '.join(sorted(SUPPORTED_EXTENSIONS))}。"
            )

        try:
            stat = file_path.stat()
        except OSError as exc:
            raise DocumentParseError(f"无法读取文件属性: {file_path}") from exc

        if extension == ".pdf":
            raw_text = self._read_pdf(file_path)
        elif extension == ".docx":
            raw_text = self._read_docx(file_path)
        else:
            raw_text = self._read_text(file_path)

        cleaned = clean_text(raw_text)
        if not cleaned:
            raise DocumentParseError(
                f"文件未提取到文本，可能是扫描版 PDF 或空文件: {file_path.name}"
            )

        chunks = chunk_text(
            cleaned,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        doc_id = self._build_doc_id(file_path, stat.st_size, stat.st_mtime)
        modified_at = datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        ).isoformat()
        title = file_path.stem

        return ParsedDocument(
            doc_id=doc_id,
            path=str(file_path),
            filename=file_path.name,
            extension=extension,
            title=title,
            text=cleaned,
            chunks=chunks,
            modified_at=modified_at,
            file_size=stat.st_size,
        )

    def parse_paths(self, paths: Iterable[str | Path]) -> list[ParsedDocument]:
        """Parse files while preserving per-file errors for the caller."""

        documents: list[ParsedDocument] = []
        for item in paths:
            try:
                documents.append(self.parse_file(item))
            except DocumentParseError:
                logger.exception("Failed to parse document: %s", item)
        return documents

    @staticmethod
    def collect_files(path: str | Path, *, recursive: bool = True) -> list[Path]:
        """Collect supported files from a file or directory."""

        target = Path(path).expanduser()
        try:
            target = target.resolve(strict=True)
        except FileNotFoundError as exc:
            raise DocumentParseError(f"路径不存在: {target}") from exc
        except OSError as exc:
            raise DocumentParseError(f"路径不可访问: {target}") from exc

        if target.is_file():
            if not DocumentParser.is_supported(target):
                raise DocumentParseError(f"不支持的文件类型: {target}")
            return [target]

        if not target.is_dir():
            raise DocumentParseError(f"既不是文件也不是目录: {target}")

        iterator = target.rglob("*") if recursive else target.glob("*")
        files = sorted(
            item.resolve()
            for item in iterator
            if item.is_file() and DocumentParser.is_supported(item)
        )
        return files

    @staticmethod
    def _read_pdf(path: Path) -> str:
        try:
            from PyPDF2 import PdfReader
        except ImportError as exc:
            raise DocumentParseError(
                "缺少 PyPDF2，请执行 pip install -r requirements.txt。"
            ) from exc

        try:
            with path.open("rb") as file_obj:
                reader = PdfReader(file_obj)
                if reader.is_encrypted:
                    try:
                        if reader.decrypt("") == 0:
                            raise DocumentParseError(
                                f"PDF 已加密，无法读取: {path.name}"
                            )
                    except Exception as exc:
                        raise DocumentParseError(
                            f"PDF 已加密或密码错误: {path.name}"
                        ) from exc

                page_texts: list[str] = []
                for page_number, page in enumerate(reader.pages, start=1):
                    try:
                        text = page.extract_text() or ""
                    except Exception as exc:
                        logger.warning(
                            "PDF 第 %s 页提取失败 (%s): %s",
                            page_number,
                            path.name,
                            exc,
                        )
                        text = ""
                    if text.strip():
                        page_texts.append(f"[第 {page_number} 页]\n{text}")
        except DocumentParseError:
            raise
        except Exception as exc:
            raise DocumentParseError(f"PDF 读取失败 {path.name}: {exc}") from exc

        return "\n\n".join(page_texts)

    @staticmethod
    def _read_docx(path: Path) -> str:
        try:
            from docx import Document
        except ImportError as exc:
            raise DocumentParseError(
                "缺少 python-docx，请执行 pip install -r requirements.txt。"
            ) from exc

        try:
            document = Document(str(path))
            sections: list[str] = []

            for paragraph in document.paragraphs:
                text = paragraph.text.strip()
                if text:
                    sections.append(text)

            for table in document.tables:
                for row in table.rows:
                    values = [cell.text.strip() for cell in row.cells]
                    row_text = " | ".join(value for value in values if value)
                    if row_text:
                        sections.append(row_text)

            for section in document.sections:
                for paragraph in section.header.paragraphs:
                    text = paragraph.text.strip()
                    if text:
                        sections.append(text)
                for paragraph in section.footer.paragraphs:
                    text = paragraph.text.strip()
                    if text:
                        sections.append(text)

        except Exception as exc:
            raise DocumentParseError(f"DOCX 读取失败 {path.name}: {exc}") from exc

        return "\n\n".join(sections)

    @staticmethod
    def _read_text(path: Path) -> str:
        encodings = ("utf-8-sig", "utf-8", "gb18030", "utf-16")
        last_error: Exception | None = None

        for encoding in encodings:
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError as exc:
                last_error = exc
            except OSError as exc:
                raise DocumentParseError(
                    f"文本文件读取失败 {path.name}: {exc}"
                ) from exc

        raise DocumentParseError(
            f"无法识别文本编码 {path.name}: {last_error}"
        )

    @staticmethod
    def _build_doc_id(path: Path, file_size: int, modified_time: float) -> str:
        raw = f"{path}|{file_size}|{modified_time:.6f}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def clean_text(text: str) -> str:
    """Normalize whitespace and remove control characters."""

    if not text:
        return ""

    normalized = unicodedata.normalize("NFKC", text)
    normalized = (
        normalized.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u00a0", " ")
    )
    normalized = "".join(
        char
        for char in normalized
        if char in {"\n", "\t"} or unicodedata.category(char)[0] != "C"
    )
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def chunk_text(
    text: str,
    *,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> list[Chunk]:
    """Split text with a sliding character window and natural boundaries."""

    if chunk_size < 100:
        raise ValueError("chunk_size 不能小于 100。")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 必须大于等于 0 且小于 chunk_size。")

    cleaned = clean_text(text)
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [Chunk(text=cleaned, index=0, start_char=0, end_char=len(cleaned))]

    boundaries = ("\n\n", "。", "！", "？", ". ", "! ", "? ", "\n", "；", ";")
    chunks: list[Chunk] = []
    start = 0
    index = 0
    text_length = len(cleaned)

    while start < text_length:
        target_end = min(start + chunk_size, text_length)
        end = target_end

        if target_end < text_length:
            search_start = start + int(chunk_size * 0.55)
            best_boundary = -1
            for marker in boundaries:
                position = cleaned.rfind(marker, search_start, target_end)
                if position > best_boundary:
                    best_boundary = position + len(marker)
            if best_boundary > start:
                end = best_boundary

        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(
                Chunk(
                    text=piece,
                    index=index,
                    start_char=start,
                    end_char=end,
                )
            )
            index += 1

        if end >= text_length:
            break

        next_start = end - chunk_overlap
        if next_start <= start:
            next_start = start + max(1, chunk_size - chunk_overlap)
        start = next_start

    return chunks


def merge_pdf_files(
    input_paths: Iterable[str | Path],
    output_path: str | Path,
) -> Path:
    """Merge PDFs with PyPDF2 and write atomically to the target path."""

    try:
        from PyPDF2 import PdfReader, PdfWriter
    except ImportError as exc:
        raise DocumentParseError(
            "缺少 PyPDF2，请执行 pip install -r requirements.txt。"
        ) from exc

    sources = [Path(path).expanduser().resolve() for path in input_paths]
    if not sources:
        raise DocumentParseError("至少需要一个 PDF 输入文件。")

    target = Path(output_path).expanduser().resolve()
    if target.suffix.lower() != ".pdf":
        target = target.with_suffix(".pdf")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_target = target.with_suffix(target.suffix + ".tmp")

    writer = PdfWriter()
    try:
        for source in sources:
            if not source.is_file():
                raise DocumentParseError(f"PDF 文件不存在: {source}")
            with source.open("rb") as file_obj:
                reader = PdfReader(file_obj)
                if reader.is_encrypted:
                    try:
                        if reader.decrypt("") == 0:
                            raise DocumentParseError(
                                f"PDF 已加密，无法合并: {source.name}"
                            )
                    except Exception as exc:
                        raise DocumentParseError(
                            f"PDF 已加密或密码错误: {source.name}"
                        ) from exc
                for page in reader.pages:
                    writer.add_page(page)

        with temporary_target.open("wb") as output_file:
            writer.write(output_file)
        temporary_target.replace(target)
    except DocumentParseError:
        if temporary_target.exists():
            temporary_target.unlink(missing_ok=True)
        raise
    except Exception as exc:
        if temporary_target.exists():
            temporary_target.unlink(missing_ok=True)
        raise DocumentParseError(f"PDF 合并写回失败: {exc}") from exc
    finally:
        writer.close()

    return target
