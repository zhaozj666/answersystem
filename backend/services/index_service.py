from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from .chunking_service import ChunkRecord, ChunkingService
from .document_loader import DocumentLoader
from .embedding_service import EmbeddingService
from .retrieval_service import RetrievalService
from .vector_store import VectorStore

Chunk = ChunkRecord


class IndexService:
    def __init__(
        self,
        docs_dir: Path,
        index_dir: Path | None = None,
        embedding_service: EmbeddingService | None = None,
    ):
        self.docs_dir = docs_dir
        self.index_dir = index_dir or self._default_index_dir(docs_dir)
        self.loader = DocumentLoader(docs_dir)
        self.chunking_service = ChunkingService()
        self._custom_embedding_service = embedding_service
        self.embedding_service = embedding_service or EmbeddingService.low_memory_default()
        self.vector_store = VectorStore(self.index_dir)
        self.retrieval_service = RetrievalService(self.embedding_service)
        self.chunks: List[Chunk] = []
        self.last_indexed_at: str | None = None
        self.last_index_file_count = 0
        self.last_errors: List[Dict[str, str]] = []
        self.supported_formats = ["PDF", "DOCX", "TXT", "MD"]
        self.embedding_provider = self.embedding_service.provider_name
        self.embedding_model = self.embedding_service.model_name or ""
        self.embedding_quality = self.embedding_service.embedding_quality
        self.embedding_fallback_reason: str | None = None
        self._load_existing_index()

    @property
    def is_index_ready(self) -> bool:
        return len(self.chunks) > 0

    def set_embedding_service(self, embedding_service: EmbeddingService) -> None:
        self._custom_embedding_service = embedding_service
        self.embedding_service = embedding_service
        self.retrieval_service = RetrievalService(self.embedding_service)

    def status(self) -> Dict[str, object]:
        return {
            "docs_dir": str(self.docs_dir),
            "file_count": self.last_index_file_count,
            "chunk_count": len(self.chunks),
            "vector_count": len([chunk for chunk in self.chunks if chunk.embedding]),
            "supported_formats": self.supported_formats,
            "last_indexed_at": self.last_indexed_at,
            "is_index_ready": self.is_index_ready,
            "retrieval": "rag_vector_local",
            "embedding_provider": self.embedding_provider,
            "embedding_model": self.embedding_model,
            "embedding_quality": self.embedding_quality,
            "fallback_reason": self.embedding_fallback_reason,
            "index_path": str(self.index_dir),
        }

    def reindex(self) -> Dict[str, object]:
        if self._custom_embedding_service is None:
            self.embedding_service = EmbeddingService.low_memory_default()
        else:
            self.embedding_service = self._custom_embedding_service
        self.retrieval_service = RetrievalService(self.embedding_service)

        files = self.loader.scan_files()
        self.last_index_file_count = len(files)
        self.last_errors = []
        chunks: List[Chunk] = []

        for file_path in files:
            try:
                loaded = self.loader.load_file(file_path)
                doc_id = self.chunking_service.build_doc_id(file_path.name)
                file_chunks = self.chunking_service.chunk_document(
                    doc_id=doc_id,
                    file_name=file_path.name,
                    text=loaded.text,
                )
                if not file_chunks:
                    self.last_errors.append(
                        {"file": file_path.name, "error": "文件文本为空，可能是扫描版或内容不可提取"}
                    )
                    continue

                for chunk in file_chunks:
                    chunk.embedding = self.embedding_service.embed(chunk.text)
                chunks.extend(file_chunks)
                print(f"[INDEX] 生成片段: {file_path.name}, 片段数={len(file_chunks)}")
            except Exception as exc:  # noqa: BLE001
                self.last_errors.append({"file": file_path.name, "error": str(exc)})
                print(f"[INDEX][ERROR] {file_path.name}: {exc}")

        self.chunks = chunks
        embedding_meta = self.embedding_service.describe()
        self.embedding_provider = str(embedding_meta.get("embedding_provider") or self.embedding_service.provider_name)
        self.embedding_model = str(embedding_meta.get("embedding_model") or "")
        self.embedding_quality = str(embedding_meta.get("embedding_quality") or "fallback")
        self.embedding_fallback_reason = (
            str(embedding_meta.get("fallback_reason")) if embedding_meta.get("fallback_reason") else None
        )

        manifest = self.vector_store.save(
            chunks=self.chunks,
            embedding_provider=self.embedding_provider,
            embedding_model=self.embedding_model,
            embedding_quality=self.embedding_quality,
            fallback_reason=self.embedding_fallback_reason,
            docs_dir=self.docs_dir,
            file_count=len(files),
        )
        self.embedding_provider = str(manifest.get("embedding_provider") or self.embedding_provider)
        self.embedding_model = str(manifest.get("embedding_model") or self.embedding_model)
        self.embedding_quality = str(manifest.get("embedding_quality") or self.embedding_quality)
        self.embedding_fallback_reason = (
            str(manifest.get("fallback_reason")) if manifest.get("fallback_reason") else self.embedding_fallback_reason
        )
        self.last_indexed_at = str(manifest.get("indexed_at") or "")
        print(f"[INDEX] 总片段数={len(self.chunks)}")

        return {
            "docs_dir": str(self.docs_dir),
            "file_count": len(files),
            "chunk_count": len(self.chunks),
            "vector_count": len(self.chunks),
            "embedding_provider": self.embedding_provider,
            "embedding_model": self.embedding_model,
            "embedding_quality": self.embedding_quality,
            "fallback_reason": self.embedding_fallback_reason,
            "index_path": str(self.index_dir),
            "errors": self.last_errors,
            "last_indexed_at": self.last_indexed_at,
            "is_index_ready": self.is_index_ready,
            "retrieval": "rag_vector_local",
        }

    def search(self, question: str, top_k: int = 5) -> List[Tuple[float, Chunk]]:
        results = self.retrieval_service.search(
            question=question,
            chunks=self.chunks,
            top_k=top_k,
            use_vector=self.vector_store.exists(),
        )
        chunk_map = {chunk.chunk_id: chunk for chunk in self.chunks}
        matched: List[Tuple[float, Chunk]] = []
        for item in results:
            chunk = chunk_map.get(str(item.get("chunk_id") or ""))
            if not chunk:
                continue
            chunk.retrieval_type = str(item.get("retrieval_type") or "vector")
            matched.append((float(item.get("score") or 0.0), chunk))
        return matched

    def _load_existing_index(self) -> None:
        chunks, manifest = self.vector_store.load()
        if not chunks:
            return
        self.chunks = chunks
        self.last_indexed_at = str(manifest.get("indexed_at") or "")
        self.last_index_file_count = int(manifest.get("file_count") or 0)
        self.embedding_provider = str(manifest.get("embedding_provider") or self.embedding_provider)
        self.embedding_model = str(manifest.get("embedding_model") or self.embedding_model)
        self.embedding_quality = str(manifest.get("embedding_quality") or self.embedding_quality)
        self.embedding_fallback_reason = (
            str(manifest.get("fallback_reason")) if manifest.get("fallback_reason") else self.embedding_fallback_reason
        )

    def _default_index_dir(self, docs_dir: Path) -> Path:
        if docs_dir.parent.name == "docs":
            return docs_dir.parent.parent / "runtime" / "rag_index"
        if docs_dir.name == "policies" and docs_dir.parent.name == "docs":
            return docs_dir.parent.parent / "runtime" / "rag_index"
        return docs_dir / "runtime" / "rag_index"
