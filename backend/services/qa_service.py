from __future__ import annotations

from typing import Dict

from .index_service import IndexService
from .llm_service import LLMClient, LLMError


class QAService:
    def __init__(self, index_service: IndexService, llm_client: LLMClient | None = None):
        self.index_service = index_service
        self.llm_client = llm_client or LLMClient()

    def ask(self, question: str, settings: Dict[str, object] | None = None) -> Dict[str, object]:
        if not self.index_service.is_index_ready:
            return {
                "answer": "知识库尚未建立索引，请联系管理员先执行“重建索引”。",
                "sources": [],
                "mode": "empty_index",
            }

        runtime_settings = settings or {}
        top_k = int(runtime_settings.get("top_k") or 5)
        candidates = self.index_service.search(question, top_k=top_k)

        print(f"[ASK] 用户问题: {question}")
        print(f"[ASK] 命中的候选片段数: {len(candidates)}")
        for index, (score, chunk) in enumerate(candidates[:5], start=1):
            preview = chunk.text[:80].replace("\n", " ").encode("gbk", errors="ignore").decode("gbk")
            print(f"[ASK] Top{index} score={score:.4f} file={chunk.file_name} preview={preview}")

        if not candidates:
            return {
                "answer": "未检索到明确依据，请补充更具体的问题或先完善制度文档。",
                "sources": [],
                "mode": "no_context",
            }

        contexts = [chunk for _, chunk in candidates]
        mode = "llm" if runtime_settings.get("enabled") else "extractive"
        try:
            answer = self.llm_client.generate_answer(question, contexts, runtime_settings)
        except LLMError as exc:
            answer = f"大模型调用失败：{exc}\n\n{self.llm_client.extractive_answer(question, contexts)}"
            mode = "extractive_fallback"

        return {
            "answer": answer,
            "sources": [
                {
                    "file": chunk.file_name,
                    "snippet": chunk.text[:220],
                    "score": round(score, 4),
                }
                for score, chunk in candidates
            ],
            "top_score": round(candidates[0][0], 4),
            "mode": mode,
        }
