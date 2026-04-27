from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.services.index_service import IndexService
from backend.services.qa_service import QAService


class FakeLLMClient:
    def __init__(self) -> None:
        self.calls = []

    def generate_answer(self, question, contexts, settings):
        self.calls.append((question, contexts, settings))
        return "根据制度，正式员工需完成试用期并通过转正审批。"


class RagPipelineTest(unittest.TestCase):
    def test_reindex_builds_vectors_for_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp)
            (docs_dir / "policy.md").write_text(
                "正式员工是指完成试用期并通过转正审批的员工。\n年假按照司龄计算。",
                encoding="utf-8",
            )

            index = IndexService(docs_dir)
            result = index.reindex()

            self.assertEqual(result["chunk_count"], 1)
            self.assertGreater(len(index.chunks[0].embedding), 0)
            self.assertAlmostEqual(sum(v * v for v in index.chunks[0].embedding), 1.0, places=5)

    def test_ask_generates_answer_from_retrieved_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp)
            (docs_dir / "policy.md").write_text(
                "正式员工是指完成试用期并通过转正审批的员工。\n年假按照司龄计算。",
                encoding="utf-8",
            )

            index = IndexService(docs_dir)
            index.reindex()
            llm = FakeLLMClient()
            qa = QAService(index, llm_client=llm)

            result = qa.ask(
                "什么是正式员工？",
                {"provider": "ollama", "model": "qwen2.5:7b", "enabled": True},
            )

            self.assertIn("正式员工", result["answer"])
            self.assertEqual(len(result["sources"]), 1)
            self.assertEqual(llm.calls[0][0], "什么是正式员工？")
            self.assertIn("转正审批", llm.calls[0][1][0].text)


if __name__ == "__main__":
    unittest.main()
