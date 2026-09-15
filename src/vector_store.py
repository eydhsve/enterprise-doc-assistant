"""Local BGE embeddings and persistent ChromaDB vector storage."""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .config import Settings


logger = logging.getLogger(__name__)


class VectorStoreError(RuntimeError):
    """Raised for embedding or vector database failures."""


@dataclass(frozen=True)
class SearchHit:
    """One retrieval result."""

    text: str
    metadata: dict[str, Any]
    score: float
    distance: float
    vector_id: str


class LocalBGEEmbedder:
    """Run BAAI/bge-small-zh locally through sentence-transformers."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-zh",
        *,
        device: str = "cpu",
        cache_dir: str | Path | None = None,
        local_only: bool = False,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.cache_dir = Path(cache_dir).expanduser() if cache_dir else None
        self.local_only = local_only
        self._model: Any | None = None
        self._lock = threading.RLock()

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model

        with self._lock:
            if self._model is not None:
                return self._model

            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise VectorStoreError(
                    "缺少 sentence-transformers，请执行 "
                    "pip install -r requirements.txt。"
                ) from exc

            if self.cache_dir is not None:
                self.cache_dir.mkdir(parents=True, exist_ok=True)

            if self.local_only:
                os.environ.setdefault("HF_HUB_OFFLINE", "1")
                os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

            kwargs: dict[str, Any] = {"device": self.device}
            if self.cache_dir is not None:
                kwargs["cache_folder"] = str(self.cache_dir)
            kwargs["local_files_only"] = self.local_only

            try:
                self._model = SentenceTransformer(self.model_name, **kwargs)
            except TypeError:
                # Older sentence-transformers versions do not expose
                # local_files_only as a direct constructor argument.
                kwargs.pop("local_files_only", None)
                if self.local_only:
                    os.environ["HF_HUB_OFFLINE"] = "1"
                    os.environ["TRANSFORMERS_OFFLINE"] = "1"
                try:
                    self._model = SentenceTransformer(self.model_name, **kwargs)
                except Exception as exc:
                    raise VectorStoreError(
                        f"本地嵌入模型加载失败: {self.model_name}。"
                        "首次运行需联网下载模型，或设置 "
                        "EMBEDDING_LOCAL_ONLY=false 并检查缓存目录。"
                    ) from exc
            except Exception as exc:
                raise VectorStoreError(
                    f"本地嵌入模型加载失败: {self.model_name}。"
                    "请检查网络、模型缓存目录和 sentence-transformers 版本。"
                ) from exc

            return self._model

    def encode(
        self,
        texts: Iterable[str],
        *,
        batch_size: int = 32,
    ) -> list[list[float]]:
        """Encode texts locally. No external embedding API is used."""

        text_list = [text if isinstance(text, str) else str(text) for text in texts]
        if not text_list:
            return []

        model = self._load_model()
        try:
            vectors = model.encode(
                text_list,
                batch_size=batch_size,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
        except Exception as exc:
            raise VectorStoreError(f"文本向量化失败: {exc}") from exc

        try:
            return [vector.tolist() for vector in vectors]
        except AttributeError:
            return [list(vector) for vector in vectors]

    def encode_query(self, query: str) -> list[float]:
        """Encode a retrieval query with the BGE Chinese instruction."""

        text = (query or "").strip()
        if not text:
            raise VectorStoreError("检索问题不能为空。")
        instruction = "为这个句子生成表示以用于检索相关文章："
        return self.encode([instruction + text])[0]


class ChromaVectorStore:
    """Persistent local ChromaDB collection."""

    def __init__(
        self,
        settings: Settings,
        embedder: LocalBGEEmbedder | None = None,
    ) -> None:
        self.settings = settings
        self.embedder = embedder or LocalBGEEmbedder(
            model_name=settings.embedding_model_name,
            device=settings.embedding_device,
            cache_dir=settings.embedding_cache_dir,
            local_only=settings.embedding_local_only,
        )
        self.persist_dir = settings.chroma_persist_dir
        self.collection_name = settings.chroma_collection
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client: Any | None = None
        self._collection: Any | None = None
        self._lock = threading.RLock()

    def _get_collection(self) -> Any:
        if self._collection is not None:
            return self._collection

        with self._lock:
            if self._collection is not None:
                return self._collection

            try:
                import chromadb
            except ImportError as exc:
                raise VectorStoreError(
                    "缺少 chromadb，请执行 pip install -r requirements.txt。"
                ) from exc

            try:
                self._client = chromadb.PersistentClient(
                    path=str(self.persist_dir)
                )
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as exc:
                raise VectorStoreError(
                    f"ChromaDB 初始化失败: {self.persist_dir}: {exc}"
                ) from exc

            return self._collection

    def add_chunks(
        self,
        *,
        doc_id: str,
        source: str,
        chunks: Iterable[Any],
        document: Any,
    ) -> int:
        """Embed and upsert chunks after replacing the same document."""

        chunk_list = list(chunks)
        if not chunk_list:
            return 0

        text_list = [chunk.text for chunk in chunk_list]
        vectors = self.embedder.encode(text_list)
        ids = [f"{doc_id}:{chunk.index}" for chunk in chunk_list]
        metadatas = [
            self._sanitize_metadata(chunk.to_metadata(document))
            for chunk in chunk_list
        ]

        try:
            collection = self._get_collection()
            collection.delete(where={"doc_id": doc_id})
            collection.upsert(
                ids=ids,
                documents=text_list,
                metadatas=metadatas,
                embeddings=vectors,
            )
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(
                f"写入 ChromaDB 失败 ({source}): {exc}"
            ) from exc

        return len(chunk_list)

    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        source_filter: str | None = None,
    ) -> list[SearchHit]:
        """Retrieve nearest chunks from the local collection."""

        normalized_query = (query or "").strip()
        if not normalized_query:
            return []

        requested_k = max(1, int(top_k or self.settings.retrieval_top_k))
        try:
            collection = self._get_collection()
            total = collection.count()
            if total == 0:
                return []

            query_vector = self.embedder.encode_query(normalized_query)
            # Fetch extra candidates when a source filter is requested.
            n_results = min(
                total,
                requested_k * 3 if source_filter else requested_k,
            )
            result = collection.query(
                query_embeddings=[query_vector],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(f"ChromaDB 检索失败: {exc}") from exc

        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        hits: list[SearchHit] = []
        filter_value = (source_filter or "").strip().lower()
        for vector_id, text, metadata, distance in zip(
            ids, documents, metadatas, distances
        ):
            metadata_dict = dict(metadata or {})
            if filter_value:
                source = str(metadata_dict.get("source", "")).lower()
                filename = str(metadata_dict.get("filename", "")).lower()
                if filter_value not in source and filter_value not in filename:
                    continue

            distance_value = float(distance)
            hits.append(
                SearchHit(
                    vector_id=vector_id,
                    text=text or "",
                    metadata=metadata_dict,
                    distance=distance_value,
                    score=1.0 - distance_value,
                )
            )
            if len(hits) >= requested_k:
                break

        return hits

    def get_document_chunks(
        self,
        doc_id: str,
        *,
        max_chunks: int = 200,
    ) -> list[SearchHit]:
        """Return all known chunks for one document in source order."""

        if not doc_id:
            return []

        try:
            collection = self._get_collection()
            result = collection.get(
                where={"doc_id": doc_id},
                limit=max(1, max_chunks),
                include=["documents", "metadatas"],
            )
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(f"读取文档分块失败: {exc}") from exc

        ids = result.get("ids") or []
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        hits = [
            SearchHit(
                vector_id=vector_id,
                text=text or "",
                metadata=dict(metadata or {}),
                score=0.0,
                distance=0.0,
            )
            for vector_id, text, metadata in zip(ids, documents, metadatas)
        ]
        hits.sort(
            key=lambda item: int(item.metadata.get("chunk_index", 0))
        )
        return hits

    def find_document_id(self, source: str) -> str | None:
        """Find one document id by full source path or filename."""

        query = (source or "").strip().lower()
        if not query:
            return None

        for document in self.list_documents():
            full_source = str(document.get("source", "")).lower()
            filename = str(document.get("filename", "")).lower()
            if query == full_source or query == filename:
                return str(document.get("doc_id", "")) or None
        for document in self.list_documents():
            full_source = str(document.get("source", "")).lower()
            filename = str(document.get("filename", "")).lower()
            if query in full_source or query in filename:
                return str(document.get("doc_id", "")) or None
        return None

    def list_documents(self) -> list[dict[str, Any]]:
        """Aggregate chunk metadata into a document list."""

        try:
            collection = self._get_collection()
            if collection.count() == 0:
                return []
            result = collection.get(include=["metadatas"])
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(f"读取文档列表失败: {exc}") from exc

        documents: dict[str, dict[str, Any]] = {}
        for metadata in result.get("metadatas") or []:
            item = dict(metadata or {})
            doc_id = str(item.get("doc_id", ""))
            if not doc_id:
                continue
            if doc_id not in documents:
                documents[doc_id] = {
                    "doc_id": doc_id,
                    "source": str(item.get("source", "")),
                    "filename": str(item.get("filename", "")),
                    "title": str(item.get("title", "")),
                    "extension": str(item.get("extension", "")),
                    "chunks": 0,
                }
            documents[doc_id]["chunks"] += 1

        return sorted(
            documents.values(),
            key=lambda item: str(item.get("filename", "")).lower(),
        )

    def delete_document(self, doc_id: str) -> None:
        if not doc_id:
            return
        try:
            self._get_collection().delete(where={"doc_id": doc_id})
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(f"删除文档失败 {doc_id}: {exc}") from exc

    def reset(self) -> None:
        """Delete and recreate the configured collection."""

        with self._lock:
            try:
                import chromadb

                if self._client is None:
                    self._client = chromadb.PersistentClient(
                        path=str(self.persist_dir)
                    )
                try:
                    self._client.delete_collection(self.collection_name)
                except Exception:
                    logger.info(
                        "Collection %s did not exist before reset.",
                        self.collection_name,
                    )
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            except VectorStoreError:
                raise
            except Exception as exc:
                raise VectorStoreError(f"清空知识库失败: {exc}") from exc

    def count(self) -> int:
        try:
            return int(self._get_collection().count())
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(f"读取知识库数量失败: {exc}") from exc

    @staticmethod
    def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                clean[str(key)] = value
            else:
                clean[str(key)] = str(value)
        return clean
