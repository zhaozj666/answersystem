from __future__ import annotations

from typing import Dict

from .index_service import IndexService


class QAService:
    def __init__(self, index_service: IndexService):
        self.index_service = index_service

    def ask(self, question: str) -> Dict[str, object]:
        if not self.index_service.is_index_ready:
            return {
                "answer": "知识库尚未建立索引，请先点击“重建索引”。",
                "sources": [],
            }

        print(f"[ASK] 用户问题: {question}")
        candidates = self.index_service.search(question, top_k=3)
        print(f"[ASK] 命中的候选片段数: {len(candidates)}")
        for i, (score, chunk) in enumerate(candidates[:3], start=1):
            preview = chunk.text[:80].replace("\n", " ")
            print(f"[ASK] Top{i} score={score:.4f} file={chunk.file_name} preview={preview}")

        if not candidates:
            return {
                "answer": "未检索到明确依据，请补充更具体的问题或先完善制度文档。",
                "sources": [],
            }

        best_score, best_chunk = candidates[0]
        answer = best_chunk.text[:260]

        sources = [
            {
                "file": chunk.file_name,
                "snippet": chunk.text[:160],
                "score": round(score, 4),
            }
            for score, chunk in candidates
        ]

        return {
            "answer": answer,
            "sources": sources,
            "top_score": round(best_score, 4),
        }
