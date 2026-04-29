from __future__ import annotations

import math
import re
from typing import Dict, List

from .chunking_service import ChunkRecord
from .embedding_service import EmbeddingService


class RetrievalService:
    """检索服务：根据向量相似度或关键词匹配从内容片段中排名返回最相关结果。"""
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service

    def search(self, question: str, chunks: List[ChunkRecord], top_k: int = 5, use_vector: bool = True) -> List[Dict[str, object]]:
        """选择向量检索或关键词检索，返回排名前 top_k 的片段结果。"""
        if not chunks:
            return []
        if use_vector and all(chunk.embedding for chunk in chunks):
            return self._vector_search(question, chunks, top_k=top_k)
        return self._keyword_search(question, chunks, top_k=top_k)

    def search_with_query_vector(
        self,
        question: str,
        query_vector: List[float],
        chunks: List[ChunkRecord],
        top_k: int = 5,
    ) -> List[Dict[str, object]]:
        if not chunks:
            return []
        return self._vector_search_from_query_vector(question, query_vector, chunks, top_k=top_k)

    def _vector_search(self, question: str, chunks: List[ChunkRecord], top_k: int) -> List[Dict[str, object]]:
        query_vector = self.embedding_service.embed(question)
        return self._vector_search_from_query_vector(question, query_vector, chunks, top_k=top_k)

    def _vector_search_from_query_vector(
        self,
        question: str,
        query_vector: List[float],
        chunks: List[ChunkRecord],
        top_k: int,
    ) -> List[Dict[str, object]]:
        scored = [
            {
                "chunk_id": chunk.chunk_id,
                "file": chunk.file_name,
                "title_path": chunk.title_path,
                "snippet": chunk.text[:220],
                "score": round(self.embedding_service.similarity(query_vector, chunk.embedding), 4),
                "retrieval_type": "vector",
            }
            for chunk in chunks
        ]
        scored.sort(key=lambda item: float(item["score"]), reverse=True)
        positives = [item for item in scored[:top_k] if float(item["score"]) > 0]
        if positives:
            return positives
        return self._keyword_search(question, chunks, top_k=top_k)

    def _keyword_search(self, question: str, chunks: List[ChunkRecord], top_k: int) -> List[Dict[str, object]]:
        query_tokens = self._tokenize(question)
        query_tf: Dict[str, int] = {}
        for token in query_tokens:
            query_tf[token] = query_tf.get(token, 0) + 1

        idf = self._build_idf(chunks)
        scored: List[Dict[str, object]] = []
        for chunk in chunks:
            chunk_tokens = chunk.tokens or self._tokenize(chunk.text)
            chunk_tf: Dict[str, int] = {}
            for token in chunk_tokens:
                chunk_tf[token] = chunk_tf.get(token, 0) + 1

            score = 0.0
            for token, q_count in query_tf.items():
                if token in chunk_tf:
                    score += q_count * chunk_tf[token] * idf.get(token, 1.0)

            scored.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "file": chunk.file_name,
                    "title_path": chunk.title_path,
                    "snippet": chunk.text[:220],
                    "score": round(score, 4),
                    "retrieval_type": "keyword_fallback",
                }
            )

        scored.sort(key=lambda item: float(item["score"]), reverse=True)
        positives = [item for item in scored[:top_k] if float(item["score"]) > 0]
        return positives or scored[:top_k]

    def _build_idf(self, chunks: List[ChunkRecord]) -> Dict[str, float]:
        total = len(chunks)
        df: Dict[str, int] = {}
        for chunk in chunks:
            chunk_tokens = chunk.tokens or self._tokenize(chunk.text)
            for token in set(chunk_tokens):
                df[token] = df.get(token, 0) + 1
        return {token: math.log((total + 1) / (freq + 1)) + 1 for token, freq in df.items()}

    def _tokenize(self, text: str) -> List[str]:
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
