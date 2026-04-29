from __future__ import annotations

import time
from typing import Dict, List, Tuple

from .index_service import Chunk, IndexService
from .llm_service import LLMClient, LLMError


MAX_CONTEXT_SOURCES = 3
MAX_SNIPPET_CHARS = 500
MAX_CONTEXT_CHARS = 1500

MODE_LABELS = {
    "extractive": "本地检索模式",
    "gpt": "GPT增强",
    "deepseek": "DeepSeek增强",
    "qwen": "Qwen增强",
    "ollama": "Ollama本地增强",
    "extractive_fallback": "回退到本地检索模式",
    "empty_index": "知识库未就绪",
    "no_context": "未命中制度依据",
}


class QAService:
    """问答服务：负责从检索索引获取相关片段，并在必要时调用大模型生成回答。"""
    def __init__(self, index_service: IndexService, llm_client: LLMClient | None = None):
        self.index_service = index_service
        self.llm_client = llm_client or LLMClient()
        self.fallback_client = LLMClient()

    def ask(self, question: str, settings: Dict[str, object] | None = None) -> Dict[str, object]:
        """问答入口：根据当前索引状态检索上下文，决定是否调用大模型生成或使用本地摘要。"""
        started_at = time.perf_counter()
        runtime_settings = settings or {}
        used_model = self._resolve_used_model(runtime_settings)
        debug_timing = self._empty_timing()

        # 如果向量索引文件都不存在，说明没有执行过重建索引，直接返回提示。
        if not self.index_service.vector_store.exists():
            debug_timing["total_ms"] = self._elapsed_ms(started_at)
            response = self._build_response(
                answer="当前尚未生成 RAG 向量索引，请先到系统设置中执行“重建索引”。",
                sources=[],
                mode="empty_index",
                retrieval_type="no_index",
                generation_type="extractive",
                used_model=used_model,
                fallback_reason="需要先重建索引",
                embedding_quality="fallback",
                embedding_model="",
                debug_timing=debug_timing,
            )
            self._log_timing(question, response)
            return response

        # 如果索引文件存在但当前内存中还没有加载成功的片段，说明索引尚未就绪。
        if not self.index_service.is_index_ready:
            debug_timing["total_ms"] = self._elapsed_ms(started_at)
            response = self._build_response(
                answer="知识库尚未建立索引，请联系管理员先执行“重建索引”。",
                sources=[],
                mode="empty_index",
                retrieval_type="no_index",
                generation_type="extractive",
                used_model=used_model,
                fallback_reason="需要先重建索引",
                embedding_quality=self.index_service.embedding_quality,
                embedding_model=self.index_service.embedding_model,
                debug_timing=debug_timing,
            )
            self._log_timing(question, response)
            return response

        # 确定本次检索使用的上下文片段数，并执行检索。
        max_context_sources = self._get_int_setting(runtime_settings, "max_context_sources", MAX_CONTEXT_SOURCES)
        top_k = max_context_sources
        retrieval_results, retrieval_type, retrieval_warning, retrieval_timing = self._retrieve(question, top_k=top_k)
        debug_timing.update(retrieval_timing)

        print(f"[ASK] 用户问题: {question}")
        print(f"[ASK] 命中的候选片段数: {len(retrieval_results)}")
        max_snippet_chars = self._get_int_setting(runtime_settings, "max_snippet_chars", MAX_SNIPPET_CHARS)
        max_context_chars = self._get_int_setting(runtime_settings, "max_context_chars", MAX_CONTEXT_CHARS)

        for index, item in enumerate(retrieval_results[:max_context_sources], start=1):
            preview = str(item.get("snippet") or "")[:80].replace("\n", " ")
            print(
                f"[ASK] Top{index} score={float(item.get('score') or 0.0):.4f} "
                f"file={item.get('file')} retrieval={item.get('retrieval_type')} preview={preview}"
            )

        # 如果检索结果为空，说明没有命中任何语义片段，直接返回“未检索到明确依据”。
        if not retrieval_results:
            debug_timing["total_ms"] = self._elapsed_ms(started_at)
            response = self._build_response(
                answer="未检索到明确依据。",
                sources=[],
                mode="no_context",
                retrieval_type=retrieval_type,
                generation_type="extractive",
                used_model=used_model,
                fallback_reason=retrieval_warning,
                embedding_quality=self.index_service.embedding_quality,
                embedding_model=self.index_service.embedding_model,
                debug_timing=debug_timing,
            )
            self._log_timing(question, response)
            return response

        chunk_map = {chunk.chunk_id: chunk for chunk in self.index_service.chunks}
        limited_results = self._limit_results_for_context(
            retrieval_results,
            max_context_sources=max_context_sources,
            max_snippet_chars=max_snippet_chars,
            max_context_chars=max_context_chars,
        )
        contexts = [chunk_map[item["chunk_id"]] for item in limited_results if item.get("chunk_id") in chunk_map]
        sources = self._build_sources(limited_results)
        context = self._build_context(
            sources,
            max_context_sources=max_context_sources,
            max_context_chars=max_context_chars,
        )

        if not contexts:
            debug_timing["total_ms"] = self._elapsed_ms(started_at)
            response = self._build_response(
                answer="未检索到明确依据。",
                sources=sources,
                mode="no_context",
                retrieval_type=retrieval_type,
                generation_type="extractive",
                used_model=used_model,
                fallback_reason=retrieval_warning,
                embedding_quality=self.index_service.embedding_quality,
                embedding_model=self.index_service.embedding_model,
                debug_timing=debug_timing,
            )
            self._log_timing(question, response)
            return response

        # 如果未在设置中启用大模型，则使用本地 extractive 摘要回答。
        if not runtime_settings.get("enabled"):
            answer = self.fallback_client.extractive_answer(question, contexts)
            debug_timing["total_ms"] = self._elapsed_ms(started_at)
            response = self._build_response(
                answer=answer,
                sources=sources,
                mode="extractive",
                retrieval_type=retrieval_type,
                generation_type="extractive",
                used_model=None,
                fallback_reason=retrieval_warning,
                embedding_quality=self.index_service.embedding_quality,
                embedding_model=self.index_service.embedding_model,
                debug_timing=debug_timing,
            )
            self._log_timing(question, response)
            return response

        # 尝试用大模型生成回答，启用时以模型设置为准。
        requested_mode = self._resolve_requested_mode(runtime_settings)
        llm_started_at = time.perf_counter()
        try:
            answer = self.llm_client.generate_answer(question, context, sources, runtime_settings)
            debug_timing["llm_generation_ms"] = self._elapsed_ms(llm_started_at)
            if not answer:
                fallback_answer = self.fallback_client.extractive_answer(question, contexts)
                debug_timing["total_ms"] = self._elapsed_ms(started_at)
                response = self._build_response(
                    answer=fallback_answer,
                    sources=sources,
                    mode="extractive",
                    retrieval_type=retrieval_type,
                    generation_type="extractive",
                    used_model=used_model,
                    fallback_reason=retrieval_warning,
                    embedding_quality=self.index_service.embedding_quality,
                    embedding_model=self.index_service.embedding_model,
                    debug_timing=debug_timing,
                )
                self._log_timing(question, response)
                return response

            debug_timing["total_ms"] = self._elapsed_ms(started_at)
            response = self._build_response(
                answer=answer,
                sources=sources,
                mode=requested_mode,
                retrieval_type=retrieval_type,
                generation_type="llm",
                used_model=used_model,
                fallback_reason=retrieval_warning,
                embedding_quality=self.index_service.embedding_quality,
                embedding_model=self.index_service.embedding_model,
                debug_timing=debug_timing,
            )
            self._log_timing(question, response)
            return response
        except LLMError as exc:
            debug_timing["llm_generation_ms"] = self._elapsed_ms(llm_started_at)
            fallback_answer = self.fallback_client.extractive_answer(question, contexts)
            debug_timing["total_ms"] = self._elapsed_ms(started_at)
            response = self._build_response(
                answer=fallback_answer,
                sources=sources,
                mode="extractive_fallback",
                retrieval_type=retrieval_type,
                generation_type="fallback",
                used_model=used_model,
                fallback_reason=str(exc),
                embedding_quality=self.index_service.embedding_quality,
                embedding_model=self.index_service.embedding_model,
                debug_timing=debug_timing,
            )
            self._log_timing(question, response)
            return response

    def _retrieve(
        self,
        question: str,
        top_k: int,
    ) -> Tuple[List[Dict[str, object]], str, str | None, Dict[str, int]]:
        """执行检索流程：优先使用向量检索，失败时回退到关键词检索。"""
        retrieval_started_at = time.perf_counter()
        timing = self._empty_timing()

        # 真实 Embedding 模式下，如果当前查询服务不可用，则回退关键词检索。
        if self.index_service.embedding_quality == "real" and not self.index_service.embedding_service.is_real_enabled_and_configured():
            warning = "当前索引基于真实 Embedding 构建，但当前未配置可用的真实 Embedding 查询服务，已回退关键词检索。"
            print(f"[ASK][WARN] {warning}")
            results = self.index_service.retrieval_service.search(
                question=question,
                chunks=self.index_service.chunks,
                top_k=top_k,
                use_vector=False,
            )
            timing["retrieval_ms"] = self._elapsed_ms(retrieval_started_at)
            return results, "keyword_fallback", warning, timing

        try:
            embedding_started_at = time.perf_counter()
            query_vector = self.index_service.embedding_service.embed(question)
            timing["question_embedding_ms"] = self._elapsed_ms(embedding_started_at)
            results = self.index_service.retrieval_service.search_with_query_vector(
                question=question,
                query_vector=query_vector,
                chunks=self.index_service.chunks,
                top_k=top_k,
            )
            timing["retrieval_ms"] = self._elapsed_ms(retrieval_started_at)
            actual_retrieval_type = "vector"
            if results and all(str(item.get("retrieval_type") or "") == "keyword_fallback" for item in results):
                actual_retrieval_type = "keyword_fallback"
            return results, actual_retrieval_type, None, timing
        except Exception as exc:  # noqa: BLE001
            # 向量检索出现异常时，自动回退到关键词检索，避免整个问答失败。
            warning = f"向量检索失败，已回退关键词检索：{exc}"
            print(f"[ASK][WARN] {warning}")
            results = self.index_service.retrieval_service.search(
                question=question,
                chunks=self.index_service.chunks,
                top_k=top_k,
                use_vector=False,
            )
            timing["retrieval_ms"] = self._elapsed_ms(retrieval_started_at)
            return results, "keyword_fallback", warning, timing

    def _limit_results_for_context(
        self,
        retrieval_results: List[Dict[str, object]],
        *,
        max_context_sources: int,
        max_snippet_chars: int,
        max_context_chars: int,
    ) -> List[Dict[str, object]]:
        """按片段数量与字符数限制切分检索结果，确保上下文不会超过模型输入限制。"""
        limited: List[Dict[str, object]] = []
        total_chars = 0

        for item in retrieval_results[:max_context_sources]:
            snippet = str(item.get("snippet") or "").strip()[:max_snippet_chars]
            if not snippet:
                continue

            remaining = max_context_chars - total_chars
            if remaining <= 0:
                break
            if len(snippet) > remaining:
                snippet = snippet[:remaining]

            next_item = dict(item)
            next_item["snippet"] = snippet
            limited.append(next_item)
            total_chars += len(snippet)
            if total_chars >= max_context_chars:
                break

        return limited

    def _build_sources(self, retrieval_results: List[Dict[str, object]]) -> List[Dict[str, object]]:
        """从检索结果中提取前端需要展示的引用来源字段。"""
        return [
            {
                "file": item.get("file"),
                "title_path": item.get("title_path") or [],
                "snippet": item.get("snippet"),
                "score": item.get("score"),
                "retrieval_type": item.get("retrieval_type"),
            }
            for item in retrieval_results
        ]

    def _build_context(
        self,
        sources: List[Dict[str, object]],
        *,
        max_context_sources: int,
        max_context_chars: int,
    ) -> str:
        """将引用片段拼接成大模型输入上下文，包含索引编号、文档路径与片段内容。"""
        blocks: List[str] = []
        total_chars = 0

        for index, item in enumerate(sources[:max_context_sources], start=1):
            title_path = " > ".join(str(part) for part in (item.get("title_path") or []) if str(part).strip())
            header = [f"[{index}] 文件：{item.get('file') or '未知文档'}"]
            if title_path:
                header.append(f"章节：{title_path}")
            block = "\n".join(
                [
                    *header,
                    f"片段：{str(item.get('snippet') or '').strip()}",
                ]
            ).strip()

            remaining = max_context_chars - total_chars
            if remaining <= 0:
                break
            if len(block) > remaining:
                block = block[:remaining]

            blocks.append(block)
            total_chars += len(block)
            if total_chars >= max_context_chars:
                break

        return "\n\n".join(blocks).strip()[:max_context_chars]

    def _resolve_requested_mode(self, settings: Dict[str, object]) -> str:
        """解析当前用户配置中选定的模型类型。"""
        provider_name = str(settings.get("provider_name") or "").strip().lower()
        if provider_name in ("gpt", "deepseek", "qwen", "ollama"):
            return provider_name
        active_mode = str(settings.get("active_mode") or "").strip().lower()
        if active_mode in ("gpt", "deepseek", "qwen", "ollama"):
            return active_mode
        return "gpt"

    def _resolve_used_model(self, settings: Dict[str, object]) -> str | None:
        """如果启用了大模型，则返回模型名称，否则返回 None。"""
        if not settings.get("enabled"):
            return None
        model = str(settings.get("model") or "").strip()
        return model or None

    def _build_response(
        self,
        *,
        answer: str,
        sources: List[Dict[str, object]],
        mode: str,
        retrieval_type: str,
        generation_type: str,
        used_model: str | None,
        fallback_reason: str | None,
        embedding_quality: str,
        embedding_model: str,
        debug_timing: Dict[str, int],
    ) -> Dict[str, object]:
        top_score = float(sources[0].get("score") or 0.0) if sources else 0.0
        return {
            "answer": answer,
            "sources": sources,
            "top_score": top_score,
            "mode": mode,
            "mode_label": self._mode_label(mode),
            "retrieval_type": retrieval_type,
            "generation_type": generation_type,
            "used_model": used_model,
            "fallback_reason": fallback_reason,
            "embedding_quality": embedding_quality,
            "embedding_model": embedding_model,
            "debug_timing": debug_timing,
        }

    def _mode_label(self, mode: str) -> str:
        return MODE_LABELS.get(mode, "本地检索模式")

    def _empty_timing(self) -> Dict[str, int]:
        """初始化调试计时结构，用于记录问答各阶段耗时。"""
        return {
            "question_embedding_ms": 0,
            "retrieval_ms": 0,
            "llm_generation_ms": 0,
            "total_ms": 0,
        }

    def _elapsed_ms(self, started_at: float) -> int:
        return max(0, int((time.perf_counter() - started_at) * 1000))

    def _get_int_setting(self, settings: Dict[str, object], key: str, default: int) -> int:
        try:
            return int(settings.get(key) or default)
        except (TypeError, ValueError):
            return default

    def _log_timing(self, question: str, response: Dict[str, object]) -> None:
        """将问答过程的耗时信息打印到控制台，便于排查性能问题。"""
        timing = response.get("debug_timing") or {}
        print(
            "[ASK][TIMING] "
            f"question={question[:40]} "
            f"question_embedding_ms={timing.get('question_embedding_ms', 0)} "
            f"retrieval_ms={timing.get('retrieval_ms', 0)} "
            f"llm_generation_ms={timing.get('llm_generation_ms', 0)} "
            f"total_ms={timing.get('total_ms', 0)}"
        )
