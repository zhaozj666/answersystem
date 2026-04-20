from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from flask import Flask, jsonify, render_template, request

try:
    from docx import Document  # type: ignore
except Exception:  # pragma: no cover
    Document = None

try:
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover
    PdfReader = None


APP_NAME = "内部规章制度智能问答助手"
BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs" / "policies"
INDEX_PATH = BASE_DIR / "data_index.json"
ALLOWED_SUFFIX = {".txt", ".md", ".pdf", ".docx"}


@dataclass
class Chunk:
    text: str
    source: str
    tokens: List[str]


class LocalPolicyQA:
    def __init__(self, docs_dir: Path, index_path: Path):
        self.docs_dir = docs_dir
        self.index_path = index_path
        self.chunks: List[Chunk] = []
        self.idf: Dict[str, float] = {}
        if self.index_path.exists():
            self._load_index()

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower().strip()
        zh = re.findall(r"[\u4e00-\u9fff]+", text)
        en = re.findall(r"[a-z0-9_\-/]+", text)
        tokens: List[str] = []
        for seq in zh:
            if len(seq) == 1:
                tokens.append(seq)
            else:
                tokens.extend(seq[i : i + 2] for i in range(len(seq) - 1))
        tokens.extend(en)
        return tokens

    def _split_text(self, text: str, max_len: int = 280) -> List[str]:
        raw = [p.strip() for p in re.split(r"[\n\r]+", text) if p.strip()]
        chunks: List[str] = []
        buff = ""
        for para in raw:
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
        return chunks

    def _read_file(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md"}:
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".pdf":
            if PdfReader is None:
                return ""
            reader = PdfReader(str(path))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        if suffix == ".docx":
            if Document is None:
                return ""
            doc = Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return ""

    def reindex(self) -> Tuple[int, int]:
        docs = [p for p in self.docs_dir.rglob("*") if p.is_file() and p.suffix.lower() in ALLOWED_SUFFIX]
        all_chunks: List[Chunk] = []
        for path in docs:
            text = self._read_file(path)
            if not text.strip():
                continue
            for chunk_text in self._split_text(text):
                tokens = self._tokenize(chunk_text)
                if not tokens:
                    continue
                all_chunks.append(
                    Chunk(
                        text=chunk_text,
                        source=str(path.relative_to(BASE_DIR)),
                        tokens=tokens,
                    )
                )

        self.chunks = all_chunks
        self._build_idf()
        self._save_index()
        return len(docs), len(self.chunks)

    def _build_idf(self) -> None:
        n = len(self.chunks)
        df: Dict[str, int] = {}
        for c in self.chunks:
            for t in set(c.tokens):
                df[t] = df.get(t, 0) + 1
        self.idf = {t: math.log((n + 1) / (f + 1)) + 1 for t, f in df.items()}

    def _save_index(self) -> None:
        payload = {
            "chunks": [{"text": c.text, "source": c.source, "tokens": c.tokens} for c in self.chunks],
            "idf": self.idf,
        }
        self.index_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _load_index(self) -> None:
        data = json.loads(self.index_path.read_text(encoding="utf-8"))
        self.chunks = [Chunk(**item) for item in data.get("chunks", [])]
        self.idf = data.get("idf", {})

    def answer(self, question: str, top_k: int = 3) -> Dict[str, object]:
        if not self.chunks:
            return {
                "answer": "当前知识库为空。请将制度文档放入 docs/policies 后点击“重建索引”。",
                "citations": [],
            }
        q_tokens = self._tokenize(question)
        if not q_tokens:
            return {"answer": "请输入更清晰的问题，例如：差旅住宿报销上限是多少？", "citations": []}

        q_tf: Dict[str, int] = {}
        for t in q_tokens:
            q_tf[t] = q_tf.get(t, 0) + 1

        scored: List[Tuple[float, Chunk]] = []
        for c in self.chunks:
            c_tf: Dict[str, int] = {}
            for t in c.tokens:
                c_tf[t] = c_tf.get(t, 0) + 1
            score = 0.0
            for t, q_count in q_tf.items():
                if t in c_tf:
                    score += q_count * c_tf[t] * self.idf.get(t, 1.0)
            if score > 0:
                scored.append((score, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]
        if not top:
            return {
                "answer": "未在现有制度中检索到明确依据。建议补充对应制度文件，或联系HR/财务确认。",
                "citations": [],
            }

        snippets = []
        citations = []
        for idx, (_, c) in enumerate(top, 1):
            snippets.append(f"依据{idx}：{c.text[:200]}")
            citations.append({"source": c.source, "preview": c.text[:120]})

        final = (
            "以下答案基于公司制度文件检索生成，请以原文制度为准。\n\n"
            + "\n\n".join(snippets)
            + "\n\n如需我给出更精确结论，请补充：城市/岗位/费用类型/审批节点等条件。"
        )
        return {"answer": final, "citations": citations}


app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR / "static"))
qa = LocalPolicyQA(DOCS_DIR, INDEX_PATH)


@app.get("/")
def home():
    return render_template("index.html", app_name=APP_NAME)


@app.post("/api/reindex")
def api_reindex():
    doc_count, chunk_count = qa.reindex()
    return jsonify({"message": f"索引完成：{doc_count} 个文件，{chunk_count} 个片段。"})


@app.post("/api/ask")
def api_ask():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    if not question:
        return jsonify({"error": "问题不能为空"}), 400
    result = qa.answer(question)
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
