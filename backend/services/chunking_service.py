from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class ChunkRecord:
    chunk_id: str
    doc_id: str
    file_name: str
    title_path: List[str]
    text: str
    char_count: int
    token_count: int
    tokens: List[str] = field(default_factory=list)
    embedding: List[float] = field(default_factory=list)
    retrieval_type: str = "vector"


class ChunkingService:
    def __init__(self, chunk_size: int = 520, overlap: int = 80):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_document(self, doc_id: str, file_name: str, text: str) -> List[ChunkRecord]:
        lines = self._prepare_lines(text)
        if not lines:
            return []

        chunks: List[ChunkRecord] = []
        current_titles: List[str] = []
        buffer: List[str] = []

        def flush_buffer() -> None:
            nonlocal buffer
            if not buffer:
                return
            merged_text = "\n".join(buffer).strip()
            buffer = []
            if not merged_text:
                return

            for part in self._split_long_text(merged_text):
                chunk_index = len(chunks) + 1
                chunk_id = f"{doc_id}_chunk_{chunk_index:04d}"
                tokens = self.tokenize(part)
                chunks.append(
                    ChunkRecord(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        file_name=file_name,
                        title_path=list(current_titles),
                        text=part,
                        char_count=len(part),
                        token_count=len(tokens),
                        tokens=tokens,
                    )
                )

        for line in lines:
            heading = self._match_heading(line)
            if heading:
                flush_buffer()
                current_titles = self._merge_title_path(current_titles, heading["level"], heading["title"])
                body_text = str(heading.get("body_text") or "").strip()
                if body_text:
                    buffer.append(body_text)
                continue
            buffer.append(line)

        flush_buffer()

        if not chunks:
            tokens = self.tokenize("\n".join(lines))
            chunks.append(
                ChunkRecord(
                    chunk_id=f"{doc_id}_chunk_0001",
                    doc_id=doc_id,
                    file_name=file_name,
                    title_path=[],
                    text="\n".join(lines),
                    char_count=len("\n".join(lines)),
                    token_count=len(tokens),
                    tokens=tokens,
                )
            )
        return chunks

    def tokenize(self, text: str) -> List[str]:
        normalized = text.lower().strip()
        zh_segments = re.findall(r"[\u4e00-\u9fff]+", normalized)
        en_tokens = re.findall(r"[a-z0-9_\-/]+", normalized)

        tokens: List[str] = []
        for segment in zh_segments:
            if len(segment) == 1:
                tokens.append(segment)
            else:
                tokens.extend(segment[i : i + 2] for i in range(len(segment) - 1))
                tokens.extend(segment[i : i + 3] for i in range(len(segment) - 2))
        tokens.extend(en_tokens)
        return tokens or (["__fallback__"] if normalized else [])

    def build_doc_id(self, file_name: str) -> str:
        digest = hashlib.blake2b(file_name.encode("utf-8"), digest_size=6).hexdigest()
        return f"doc_{digest}"

    def _prepare_lines(self, text: str) -> List[str]:
        clean = text.replace("\u3000", " ")
        clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]+", " ", clean)
        clean = re.sub(r"[\ue000-\uf8ff]+", " ", clean)

        lines: List[str] = []
        for raw_line in clean.splitlines():
            line = re.sub(r"\s+", " ", raw_line).strip()
            if not line:
                continue
            visible = sum(1 for ch in line if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")
            if visible / max(len(line), 1) < 0.25:
                continue
            lines.append(line)
        return lines

    def _split_long_text(self, text: str) -> List[str]:
        paragraphs = [item.strip() for item in re.split(r"[\n\r]+", text) if item.strip()]
        if not paragraphs:
            paragraphs = [text.strip()]

        parts: List[str] = []
        buffer = ""
        for para in paragraphs:
            if len(buffer) + len(para) + 1 <= self.chunk_size:
                buffer = f"{buffer}\n{para}".strip()
                continue

            if buffer:
                parts.append(buffer)
            if len(para) <= self.chunk_size:
                buffer = para
            else:
                step = max(1, self.chunk_size - self.overlap)
                for index in range(0, len(para), step):
                    parts.append(para[index : index + self.chunk_size])
                buffer = ""

        if buffer:
            parts.append(buffer)
        return parts

    def _match_heading(self, line: str) -> dict[str, object] | None:
        patterns = [
            (1, r"^(第[一二三四五六七八九十百零〇0-9]+章)\s*(.+)?$"),
            (2, r"^(第[一二三四五六七八九十百零〇0-9]+条)\s*(.+)?$"),
            (3, r"^([一二三四五六七八九十]+[、.])\s*(.+)$"),
            (4, r"^(（[一二三四五六七八九十0-9]+）)\s*(.+)$"),
            (5, r"^(\d+[.、])\s*(.+)$"),
        ]
        for level, pattern in patterns:
            match = re.match(pattern, line)
            if match:
                prefix = match.group(1).strip()
                suffix = (match.group(2) or "").strip()
                return {
                    "level": level,
                    "title": f"{prefix} {suffix}".strip(),
                    "body_text": suffix if level > 1 else "",
                }
        return None

    def _merge_title_path(self, current: List[str], level: int, title: str) -> List[str]:
        next_path = list(current[: level - 1])
        next_path.append(title)
        return next_path
