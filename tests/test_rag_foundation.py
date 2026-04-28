from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.services.chunking_service import ChunkingService
from backend.services.embedding_service import EmbeddingService
from backend.services.index_service import IndexService
from backend.services.retrieval_service import RetrievalService
from backend.services.vector_store import VectorStore


class RagFoundationTest(unittest.TestCase):
    def test_chunking_service_builds_structured_chunks(self) -> None:
        service = ChunkingService()
        chunks = service.chunk_document(
            doc_id="doc-1",
            file_name="policy.md",
            text=(
                "第一章 总则\n"
                "第一条 为规范管理，制定本制度。\n"
                "第二条 正式员工应遵守考勤要求。\n\n"
                "第二章 假期\n"
                "一、年假规则\n"
                "（一）年假按照司龄计算。"
            ),
        )

        self.assertGreaterEqual(len(chunks), 2)
        first = chunks[0]
        self.assertEqual(first.doc_id, "doc-1")
        self.assertEqual(first.file_name, "policy.md")
        self.assertTrue(first.chunk_id.startswith("doc-1_chunk_"))
        self.assertGreater(first.char_count, 0)
        self.assertGreater(first.token_count, 0)
        self.assertTrue(first.title_path)

    def test_vector_store_persists_chunks_vectors_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp) / "docs" / "policies"
            index_dir = Path(tmp) / "runtime" / "rag_index"
            docs_dir.mkdir(parents=True, exist_ok=True)

            index = IndexService(docs_dir=docs_dir, index_dir=index_dir)
            index.chunks = []
            result = index.reindex()

            self.assertTrue((index_dir / "chunks.json").exists())
            self.assertTrue((index_dir / "vectors.pkl").exists())
            self.assertTrue((index_dir / "manifest.json").exists())
            self.assertEqual(result["index_path"], str(index_dir))

    def test_reindex_returns_vector_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp) / "docs" / "policies"
            docs_dir.mkdir(parents=True, exist_ok=True)
            (docs_dir / "policy.md").write_text(
                "第一章 总则\n第一条 正式员工应遵守制度。\n第二条 年假按照司龄计算。",
                encoding="utf-8",
            )

            index = IndexService(
                docs_dir=docs_dir,
                index_dir=Path(tmp) / "runtime" / "rag_index",
                embedding_service=EmbeddingService(provider_name="local_hash"),
            )
            result = index.reindex()

            self.assertEqual(result["file_count"], 1)
            self.assertGreater(result["chunk_count"], 0)
            self.assertEqual(result["vector_count"], result["chunk_count"])
            self.assertEqual(result["embedding_provider"], "local_hash")
            self.assertEqual(result["embedding_model"], "local_hash_fallback")
            self.assertEqual(result["embedding_quality"], "fallback")
            self.assertEqual(result["fallback_reason"], None)
            self.assertTrue(result["index_path"].endswith("runtime\\rag_index") or result["index_path"].endswith("runtime/rag_index"))

            manifest = VectorStore(Path(tmp) / "runtime" / "rag_index").load()[1]
            self.assertEqual(manifest["embedding_provider"], "local_hash")
            self.assertEqual(manifest["embedding_model"], "local_hash_fallback")
            self.assertEqual(manifest["embedding_quality"], "fallback")
            self.assertEqual(manifest["fallback_reason"], None)

    def test_retrieval_service_falls_back_to_keyword_search(self) -> None:
        chunking = ChunkingService()
        chunks = chunking.chunk_document(
            doc_id="doc-1",
            file_name="policy.md",
            text="第一条 正式员工应遵守考勤制度。第二条 年假按照司龄计算。",
        )
        embedding = EmbeddingService(provider_name="local_hash")
        retrieval = RetrievalService(embedding_service=embedding)

        results = retrieval.search("什么是正式员工", chunks, top_k=3, use_vector=False)

        self.assertTrue(results)
        self.assertEqual(results[0]["retrieval_type"], "keyword_fallback")
        self.assertIn("file", results[0])
        self.assertIn("title_path", results[0])
        self.assertIn("snippet", results[0])
        self.assertIn("score", results[0])


if __name__ == "__main__":
    unittest.main()
