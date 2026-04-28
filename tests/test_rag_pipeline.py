from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.services.index_service import IndexService
from backend.services.llm_service import LLMError
from backend.services.qa_service import QAService


class FakeLLMClient:
    def __init__(self) -> None:
        self.calls = []

    def generate_answer(self, question, context, sources, settings):
        self.calls.append((question, context, sources, settings))
        return "根据制度，正式员工需完成试用期并通过转正审批。[1]"


class DisabledLLMClient:
    def generate_answer(self, question, context, sources, settings):
        return None


class FailingLLMClient:
    def generate_answer(self, question, context, sources, settings):
        raise LLMError("模型接口调用失败：网络错误")


class TimeoutLLMClient:
    def generate_answer(self, question, context, sources, settings):
        raise LLMError("模型请求超过 20 秒，已回退本地摘要。")


class BrokenVectorRetrieval:
    def __init__(self, fallback_results):
        self.fallback_results = fallback_results

    def search(self, question, chunks, top_k=5, use_vector=True):
        if use_vector:
            raise RuntimeError("vector search failed")
        return self.fallback_results[:top_k]


class RagPipelineTest(unittest.TestCase):
    def test_reindex_builds_vectors_for_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp)
            (docs_dir / "policy.md").write_text(
                "第一章 总则\n第一条 正式员工是指完成试用期并通过转正审批的员工。\n第二条 年假按照司龄计算。",
                encoding="utf-8",
            )

            index = IndexService(docs_dir)
            result = index.reindex()

            self.assertGreaterEqual(result["chunk_count"], 1)
            self.assertEqual(result["vector_count"], result["chunk_count"])
            self.assertGreater(len(index.chunks[0].embedding), 0)

    def test_ask_uses_vector_retrieval_and_returns_sources_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp)
            (docs_dir / "policy.md").write_text(
                "第一章 总则\n第一条 正式员工是指完成试用期并通过转正审批的员工。\n第二条 年假按照司龄计算。",
                encoding="utf-8",
            )

            index = IndexService(docs_dir)
            index.reindex()
            qa = QAService(index, llm_client=DisabledLLMClient())

            result = qa.ask("什么是正式员工？", {"enabled": False})

            self.assertEqual(result["embedding_quality"], "fallback")
            self.assertEqual(result["embedding_model"], "local_hash_fallback")
            self.assertEqual(result["retrieval_type"], "vector")
            self.assertEqual(result["generation_type"], "extractive")
            self.assertEqual(result["mode"], "extractive")
            self.assertEqual(result["used_model"], None)
            self.assertEqual(result["fallback_reason"], None)
            self.assertIn("debug_timing", result)
            self.assertIn("question_embedding_ms", result["debug_timing"])
            self.assertIn("retrieval_ms", result["debug_timing"])
            self.assertIn("llm_generation_ms", result["debug_timing"])
            self.assertIn("total_ms", result["debug_timing"])
            self.assertTrue(result["sources"])
            self.assertIn("file", result["sources"][0])
            self.assertIn("title_path", result["sources"][0])
            self.assertIn("snippet", result["sources"][0])
            self.assertIn("score", result["sources"][0])
            self.assertIn("retrieval_type", result["sources"][0])
            self.assertEqual(result["sources"][0]["retrieval_type"], "vector")

    def test_ask_returns_no_index_when_vector_index_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp)
            (docs_dir / "policy.md").write_text(
                "第一条 正式员工应遵守制度。",
                encoding="utf-8",
            )

            index = IndexService(docs_dir)
            qa = QAService(index)

            result = qa.ask("什么是正式员工？", {"enabled": False})

            self.assertEqual(result["embedding_quality"], "fallback")
            self.assertEqual(result["embedding_model"], "")
            self.assertEqual(result["retrieval_type"], "no_index")
            self.assertEqual(result["generation_type"], "extractive")
            self.assertEqual(result["used_model"], None)
            self.assertIn("重建索引", result["answer"])

    def test_ask_falls_back_to_keyword_when_vector_retrieval_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp)
            (docs_dir / "policy.md").write_text(
                "第一章 总则\n第一条 正式员工是指完成试用期并通过转正审批的员工。",
                encoding="utf-8",
            )

            index = IndexService(docs_dir)
            index.reindex()
            fallback_results = [
                {
                    "chunk_id": index.chunks[0].chunk_id,
                    "file": index.chunks[0].file_name,
                    "title_path": index.chunks[0].title_path,
                    "snippet": index.chunks[0].text[:220],
                    "score": 1.0,
                    "retrieval_type": "keyword_fallback",
                }
            ]
            index.retrieval_service = BrokenVectorRetrieval(fallback_results)
            qa = QAService(index)

            result = qa.ask("什么是正式员工？", {"enabled": False})

            self.assertEqual(result["embedding_quality"], "fallback")
            self.assertEqual(result["embedding_model"], "local_hash_fallback")
            self.assertEqual(result["retrieval_type"], "keyword_fallback")
            self.assertEqual(result["sources"][0]["retrieval_type"], "keyword_fallback")
            self.assertEqual(result["generation_type"], "extractive")

    def test_ask_calls_llm_with_numbered_context_and_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp)
            (docs_dir / "policy.md").write_text(
                "第一章 总则\n第一条 正式员工是指完成试用期并通过转正审批的员工。",
                encoding="utf-8",
            )

            index = IndexService(docs_dir)
            index.reindex()
            llm = FakeLLMClient()
            qa = QAService(index, llm_client=llm)

            result = qa.ask("什么是正式员工？", {"provider_name": "ollama", "enabled": True, "model": "qwen2.5:3b"})

            self.assertEqual(result["embedding_quality"], "fallback")
            self.assertEqual(result["embedding_model"], "local_hash_fallback")
            self.assertEqual(result["mode"], "ollama")
            self.assertEqual(result["generation_type"], "llm")
            self.assertEqual(result["used_model"], "qwen2.5:3b")
            self.assertEqual(llm.calls[0][0], "什么是正式员工？")
            self.assertIn("[1]", llm.calls[0][1])
            self.assertIn("policy.md", llm.calls[0][1])
            self.assertTrue(llm.calls[0][2])

    def test_ask_uses_default_max_context_sources_three(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp)
            (docs_dir / "policy.md").write_text(
                "第一章 总则\n第一条 正式员工是指完成试用期并通过转正审批的员工。\n"
                "第二条 年假按照司龄计算。\n第三条 加班需要审批。\n第四条 迟到早退按考勤制度执行。",
                encoding="utf-8",
            )

            index = IndexService(docs_dir)
            index.reindex()
            qa = QAService(index, llm_client=DisabledLLMClient())

            result = qa.ask("员工制度有哪些要求？", {"enabled": False})

            self.assertLessEqual(len(result["sources"]), 3)

    def test_ask_respects_configurable_context_limits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp)
            long_text = (
                "第一章 总则\n第一条 " + ("正式员工需要遵守制度。" * 50) + "\n"
                "第二条 " + ("年假按照制度执行。" * 50) + "\n"
                "第三条 " + ("加班需要审批。" * 50) + "\n"
                "第四条 " + ("考勤异常需要说明。" * 50)
            )
            (docs_dir / "policy.md").write_text(long_text, encoding="utf-8")

            index = IndexService(docs_dir)
            index.reindex()
            llm = FakeLLMClient()
            qa = QAService(index, llm_client=llm)

            qa.ask(
                "请总结员工制度要求",
                {
                    "provider_name": "qwen",
                    "enabled": True,
                    "model": "qwen-plus",
                    "max_context_sources": 2,
                    "max_snippet_chars": 300,
                    "max_context_chars": 700,
                },
            )

            _, context, sources, _ = llm.calls[0]
            self.assertLessEqual(len(sources), 2)
            self.assertLessEqual(len(context), 700)
            for item in sources:
                self.assertLessEqual(len(item["snippet"]), 300)

    def test_ask_limits_context_before_llm_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp)
            long_text = (
                "第一章 总则\n第一条 " + ("正式员工需要遵守制度。" * 80) + "\n"
                "第二条 " + ("年假按照制度执行。" * 80) + "\n"
                "第三条 " + ("加班需要审批。" * 80) + "\n"
                "第四条 " + ("考勤异常需要说明。" * 80)
            )
            (docs_dir / "policy.md").write_text(long_text, encoding="utf-8")

            index = IndexService(docs_dir)
            index.reindex()
            llm = FakeLLMClient()
            qa = QAService(index, llm_client=llm)

            qa.ask("请总结员工制度要求", {"provider_name": "qwen", "enabled": True, "model": "qwen-plus"})

            _, context, sources, _ = llm.calls[0]
            self.assertLessEqual(len(sources), 3)
            self.assertLessEqual(len(context), 1500)
            for item in sources:
                self.assertLessEqual(len(item["snippet"]), 500)

    def test_ask_falls_back_to_extractive_when_llm_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp)
            (docs_dir / "policy.md").write_text(
                "第一章 总则\n第一条 正式员工是指完成试用期并通过转正审批的员工。",
                encoding="utf-8",
            )

            index = IndexService(docs_dir)
            index.reindex()
            qa = QAService(index, llm_client=FailingLLMClient())

            result = qa.ask("什么是正式员工？", {"provider_name": "gpt", "enabled": True, "model": "gpt-4o-mini"})

            self.assertEqual(result["embedding_quality"], "fallback")
            self.assertEqual(result["embedding_model"], "local_hash_fallback")
            self.assertEqual(result["generation_type"], "fallback")
            self.assertEqual(result["mode"], "extractive_fallback")
            self.assertEqual(result["used_model"], "gpt-4o-mini")
            self.assertIn("模型接口调用失败", result["fallback_reason"])
            self.assertIn("当前未启用大模型生成", result["answer"])

    def test_ask_falls_back_when_llm_timeout_exceeds_twenty_seconds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp)
            (docs_dir / "policy.md").write_text(
                "第一章 总则\n第一条 正式员工是指完成试用期并通过转正审批的员工。",
                encoding="utf-8",
            )

            index = IndexService(docs_dir)
            index.reindex()
            qa = QAService(index, llm_client=TimeoutLLMClient())

            result = qa.ask("什么是正式员工？", {"provider_name": "qwen", "enabled": True, "model": "qwen-plus"})

            self.assertEqual(result["generation_type"], "fallback")
            self.assertIn("20 秒", result["fallback_reason"])


if __name__ == "__main__":
    unittest.main()
