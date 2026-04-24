from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from .document_loader import DocumentLoader


@dataclass
class Chunk:
    file_name: str
    text: str
    tokens: List[str]


class IndexService:
    def __init__(self, docs_dir: Path):
        self.docs_dir = docs_dir
        self.loader = DocumentLoader(docs_dir)
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

        tokens.extend(en_tokens)

        if not tokens and text:
            tokens = ["__fallback__"]
        return tokens

    def _split_text(self, text: str, max_len: int = 320) -> List[str]:
        clean = text.replace("\u3000", " ")
        paras = [p.strip() for p in re.split(r"[\n\r]+", clean) if p.strip()]
        if not paras and clean.strip():
            paras = [clean.strip()]

        chunks: List[str] = []
        buff = ""
        for para in paras:
            if len(buff) + len(para) + 1 <= max_len:
                buff = f"{buff}\n{para}".strip()
            else:
                if buff:
                    chunks.append(buff)
                if len(para) <= max_len:
                    buff = para
                else:
                    for i in range(0, len(para), max_len):
                        chunks.append(para[i : i + max_len])
                    buff = ""

        if buff:
            chunks.append(buff)

        if not chunks and clean.strip():
            chunks.append(clean.strip()[:max_len])

        return chunks

    def _build_idf(self) -> None:
        total = len(self.chunks)
        df: Dict[str, int] = {}
        for c in self.chunks:
            for t in set(c.tokens):
                df[t] = df.get(t, 0) + 1

        self.idf = {t: math.log((total + 1) / (freq + 1)) + 1 for t, freq in df.items()}

    def status(self) -> Dict[str, object]:
        return {
            "docs_dir": str(self.docs_dir),
            "file_count": self.last_index_file_count,
            "chunk_count": len(self.chunks),
            "supported_formats": self.supported_formats,
            "last_indexed_at": self.last_indexed_at,
            "is_index_ready": self.is_index_ready,
        }

    def reindex(self) -> Dict[str, object]:
        files = self.loader.scan_files()
        self.last_index_file_count = len(files)
        self.last_errors = []

        all_chunks: List[Chunk] = []
        per_file_chunks: Dict[str, int] = {}

        for file_path in files:
            try:
                loaded = self.loader.load_file(file_path)
                if not loaded.text.strip():
                    per_file_chunks[file_path.name] = 0
                    self.last_errors.append(
                        {"file": file_path.name, "error": "文件文本为空，可能是扫描版或内容不可提取"}
                    )
                    continue

                chunk_texts = self._split_text(loaded.text)
                for ctext in chunk_texts:
                    all_chunks.append(
                        Chunk(
                            file_name=file_path.name,
                            text=ctext,
                            tokens=self._tokenize(ctext),
                        )
                    )

                per_file_chunks[file_path.name] = len(chunk_texts)
                print(f"[INDEX] 生成片段: {file_path.name}, 片段数={len(chunk_texts)}")
            except Exception as exc:  # noqa: BLE001
                per_file_chunks[file_path.name] = 0
                self.last_errors.append({"file": file_path.name, "error": str(exc)})
                print(f"[INDEX][ERROR] {file_path.name}: {exc}")

        self.chunks = all_chunks
        self._build_idf()
        self.last_indexed_at = datetime.now(timezone.utc).isoformat()

        print(f"[INDEX] 总片段数={len(self.chunks)}")

        return {
            "docs_dir": str(self.docs_dir),
            "file_count": len(files),
            "chunk_count": len(self.chunks),
            "chunks_per_file": per_file_chunks,
            "errors": self.last_errors,
            "last_indexed_at": self.last_indexed_at,
            "is_index_ready": self.is_index_ready,
        }

    def search(self, question: str, top_k: int = 3) -> List[Tuple[float, Chunk]]:
        q_tokens = self._tokenize(question)
        q_tf: Dict[str, int] = {}
        for token in q_tokens:
            q_tf[token] = q_tf.get(token, 0) + 1

        scored: List[Tuple[float, Chunk]] = []
        for chunk in self.chunks:
            c_tf: Dict[str, int] = {}
            for token in chunk.tokens:
                c_tf[token] = c_tf.get(token, 0) + 1

            score = 0.0
            for token, q_count in q_tf.items():
                if token in c_tf:
                    score += q_count * c_tf[token] * self.idf.get(token, 1.0)
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]
