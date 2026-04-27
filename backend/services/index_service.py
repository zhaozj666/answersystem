from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from .document_loader import DocumentLoader
from .embedding_service import LocalEmbeddingService


@dataclass
class Chunk:
    file_name: str
    text: str
    tokens: List[str]
    embedding: List[float]


class IndexService:
    def __init__(self, docs_dir: Path):
        self.docs_dir = docs_dir
        self.loader = DocumentLoader(docs_dir)
        self.embedding_service = LocalEmbeddingService()
        self.chunks: List[Chunk] = []
        self.idf: Dict[str, float] = {}
        self.last_indexed_at: str | None = None
        self.last_index_file_count = 0
        self.last_errors: List[Dict[str, str]] = []
        self.supported_formats = ["PDF", "DOCX", "TXT", "MD"]

    @property
    def is_index_ready(self) -> bool:
        return len(self.chunks) > 0

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower().strip()
        zh_segments = re.findall(r"[\u4e00-\u9fff]+", text)
        en_tokens = re.findall(r"[a-z0-9_\-/]+", text)

        tokens: List[str] = []
        for seg in zh_segments:
            if len(seg) == 1:
                tokens.append(seg)
            else:
                tokens.extend(seg[i : i + 2] for i in range(len(seg) - 1))
                tokens.extend(seg[i : i + 3] for i in range(len(seg) - 2))

        tokens.extend(en_tokens)
        return tokens or (["__fallback__"] if text else [])

    def _clean_text(self, text: str) -> str:
        text = text.replace("\u3000", " ")
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]+", " ", text)
        text = re.sub(r"[\ue000-\uf8ff]+", " ", text)
        lines: List[str] = []
        for line in text.splitlines():
            stripped = re.sub(r"\s+", " ", line).strip()
            if not stripped:
                continue
            visible = sum(1 for ch in stripped if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")
            if visible / max(len(stripped), 1) < 0.25:
                continue
            lines.append(stripped)
        return "\n".join(lines)

    def _split_text(self, text: str, max_len: int = 520, overlap: int = 80) -> List[str]:
        clean = self._clean_text(text)
        paras = [item.strip() for item in re.split(r"[\n\r]+", clean) if item.strip()]
        if not paras and clean.strip():
            paras = [clean.strip()]

        chunks: List[str] = []
        buffer = ""
        for para in paras:
            if len(buffer) + len(para) + 1 <= max_len:
                buffer = f"{buffer}\n{para}".strip()
                continue

            if buffer:
                chunks.append(buffer)
            if len(para) <= max_len:
                buffer = para
            else:
                step = max(1, max_len - overlap)
                for index in range(0, len(para), step):
                    chunks.append(para[index : index + max_len])
                buffer = ""

        if buffer:
            chunks.append(buffer)
        if not chunks and clean.strip():
            chunks.append(clean.strip()[:max_len])
        return chunks

    def _build_idf(self) -> None:
        total = len(self.chunks)
        df: Dict[str, int] = {}
        for chunk in self.chunks:
            for token in set(chunk.tokens):
                df[token] = df.get(token, 0) + 1
        self.idf = {token: math.log((total + 1) / (freq + 1)) + 1 for token, freq in df.items()}

    def status(self) -> Dict[str, object]:
        return {
            "docs_dir": str(self.docs_dir),
            "file_count": self.last_index_file_count,
            "chunk_count": len(self.chunks),
            "supported_formats": self.supported_formats,
            "last_indexed_at": self.last_indexed_at,
            "is_index_ready": self.is_index_ready,
            "retrieval": "local_vector_hybrid",
        }

    def reindex(self) -> Dict[str, object]:
        files = self.loader.scan_files()
        self.last_index_file_count = len(files)
        self.last_errors = []

        chunks: List[Chunk] = []
        chunks_per_file: Dict[str, int] = {}

        for file_path in files:
            try:
                loaded = self.loader.load_file(file_path)
                cleaned_text = self._clean_text(loaded.text)
                if not cleaned_text.strip():
                    chunks_per_file[file_path.name] = 0
                    self.last_errors.append(
                        {"file": file_path.name, "error": "文件文本为空，可能是扫描版或内容不可提取"}
                    )
                    continue

                chunk_texts = self._split_text(cleaned_text)
                for chunk_text in chunk_texts:
                    chunks.append(
                        Chunk(
                            file_name=file_path.name,
                            text=chunk_text,
                            tokens=self._tokenize(chunk_text),
                            embedding=self.embedding_service.embed(chunk_text),
                        )
                    )
                chunks_per_file[file_path.name] = len(chunk_texts)
                print(f"[INDEX] 生成片段: {file_path.name}, 片段数={len(chunk_texts)}")
            except Exception as exc:  # noqa: BLE001
                chunks_per_file[file_path.name] = 0
                self.last_errors.append({"file": file_path.name, "error": str(exc)})
                print(f"[INDEX][ERROR] {file_path.name}: {exc}")

        self.chunks = chunks
        self._build_idf()
        self.last_indexed_at = datetime.now(timezone.utc).isoformat()
        print(f"[INDEX] 总片段数={len(self.chunks)}")

        return {
            "docs_dir": str(self.docs_dir),
            "file_count": len(files),
            "chunk_count": len(self.chunks),
            "chunks_per_file": chunks_per_file,
            "errors": self.last_errors,
            "last_indexed_at": self.last_indexed_at,
            "is_index_ready": self.is_index_ready,
            "retrieval": "local_vector_hybrid",
        }

    def search(self, question: str, top_k: int = 5) -> List[Tuple[float, Chunk]]:
        q_tokens = self._tokenize(question)
        q_embedding = self.embedding_service.embed(question)
        q_tf: Dict[str, int] = {}
        for token in q_tokens:
            q_tf[token] = q_tf.get(token, 0) + 1

        scored: List[Tuple[float, Chunk]] = []
        for chunk in self.chunks:
            c_tf: Dict[str, int] = {}
            for token in chunk.tokens:
                c_tf[token] = c_tf.get(token, 0) + 1

            keyword_score = 0.0
            for token, q_count in q_tf.items():
                if token in c_tf:
                    keyword_score += q_count * c_tf[token] * self.idf.get(token, 1.0)

            vector_score = self.embedding_service.similarity(q_embedding, chunk.embedding)
            score = vector_score + (0.05 * keyword_score)
            scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        positives = [(score, chunk) for score, chunk in scored[:top_k] if score > 0]
        return positives or scored[:top_k]
