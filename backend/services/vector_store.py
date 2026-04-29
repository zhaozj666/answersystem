from __future__ import annotations

import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from .chunking_service import ChunkRecord


class VectorStore:
    """向量存储：持久化分片内容、Embedding 向量和索引元数据。"""
    def __init__(self, index_dir: Path):
        self.index_dir = index_dir
        self.chunks_path = index_dir / "chunks.json"
        self.vectors_path = index_dir / "vectors.pkl"
        self.manifest_path = index_dir / "manifest.json"

    def exists(self) -> bool:
        return self.chunks_path.exists() and self.vectors_path.exists() and self.manifest_path.exists()

    def save(
        self,
        chunks: List[ChunkRecord],
        embedding_provider: str,
        embedding_model: str,
        embedding_quality: str,
        fallback_reason: str | None,
        docs_dir: Path,
        file_count: int,
    ) -> Dict[str, object]:
        self.index_dir.mkdir(parents=True, exist_ok=True)

        chunk_payload = [
            {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "file_name": chunk.file_name,
                "title_path": chunk.title_path,
                "text": chunk.text,
                "char_count": chunk.char_count,
                "token_count": chunk.token_count,
                "tokens": chunk.tokens,
            }
            for chunk in chunks
        ]
        vectors_payload = [chunk.embedding for chunk in chunks]
        manifest = {
            "docs_dir": str(docs_dir),
            "file_count": file_count,
            "chunk_count": len(chunks),
            "vector_count": len(vectors_payload),
            "embedding_provider": embedding_provider,
            "embedding_model": embedding_model,
            "embedding_quality": embedding_quality,
            "fallback_reason": fallback_reason,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        }

        self.chunks_path.write_text(json.dumps(chunk_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        with self.vectors_path.open("wb") as handle:
            pickle.dump(vectors_payload, handle)
        self.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest

    def load(self) -> Tuple[List[ChunkRecord], Dict[str, object]]:
        if not self.exists():
            return [], {}

        chunk_items = json.loads(self.chunks_path.read_text(encoding="utf-8"))
        with self.vectors_path.open("rb") as handle:
            vectors = pickle.load(handle)
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))

        chunks: List[ChunkRecord] = []
        for item, vector in zip(chunk_items, vectors):
            chunks.append(
                ChunkRecord(
                    chunk_id=str(item.get("chunk_id") or ""),
                    doc_id=str(item.get("doc_id") or ""),
                    file_name=str(item.get("file_name") or ""),
                    title_path=list(item.get("title_path") or []),
                    text=str(item.get("text") or ""),
                    char_count=int(item.get("char_count") or 0),
                    token_count=int(item.get("token_count") or 0),
                    tokens=list(item.get("tokens") or []),
                    embedding=[float(value) for value in vector],
                )
            )
        return chunks, manifest
