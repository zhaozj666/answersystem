from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Dict, List

from .index_service import Chunk


class LLMError(RuntimeError):
    pass


class LLMClient:
    def generate_answer(self, question: str, contexts: List[Chunk], settings: Dict[str, object]) -> str:
        if not settings.get("enabled"):
            return self.extractive_answer(question, contexts)

        provider = str(settings.get("provider") or "ollama")
        if provider == "ollama":
            return self._call_ollama(question, contexts, settings)
        if provider == "openai_compatible":
            return self._call_openai_compatible(question, contexts, settings)
        return self.extractive_answer(question, contexts)

    def extractive_answer(self, question: str, contexts: List[Chunk]) -> str:
        if not contexts:
            return "未检索到明确依据。请补充更具体的问题，或先完善制度文档。"
        evidence = "\n\n".join(f"依据{i + 1}：{chunk.text[:260]}" for i, chunk in enumerate(contexts[:3]))
        return (
            "当前未启用大模型生成，以下为向量检索命中的制度依据摘要：\n\n"
            f"{evidence}\n\n"
            "如需更自然、可综合多段依据的回答，请联系管理员在设置中启用模型。"
        )

    def _messages(self, question: str, contexts: List[Chunk]) -> List[Dict[str, str]]:
        context_text = "\n\n".join(
            f"[{i + 1}] 来源：{chunk.file_name}\n{chunk.text}" for i, chunk in enumerate(contexts)
        )
        return [
            {
                "role": "system",
                "content": (
                    "你是企业内部制度问答助手。只允许基于给定引用回答。"
                    "如果引用不足以回答，明确说明未找到依据。"
                    "回答要简洁、准确，并在关键结论后标注引用编号，例如 [1]。"
                ),
            },
            {
                "role": "user",
                "content": f"问题：{question}\n\n可用引用：\n{context_text}",
            },
        ]

    def _call_ollama(self, question: str, contexts: List[Chunk], settings: Dict[str, object]) -> str:
        base_url = str(settings.get("base_url") or "http://127.0.0.1:11434").rstrip("/")
        payload = {
            "model": settings.get("model") or "qwen2.5:7b",
            "messages": self._messages(question, contexts),
            "stream": False,
            "options": {"temperature": float(settings.get("temperature") or 0.2)},
        }
        data = self._post_json(f"{base_url}/api/chat", payload, headers={})
        content = data.get("message", {}).get("content")
        if not content:
            raise LLMError("Ollama 未返回回答内容。")
        return str(content).strip()

    def _call_openai_compatible(
        self, question: str, contexts: List[Chunk], settings: Dict[str, object]
    ) -> str:
        base_url = str(settings.get("base_url") or "").rstrip("/")
        if not base_url:
            raise LLMError("请填写 OpenAI-compatible 接口地址。")

        headers = {}
        api_key = str(settings.get("api_key") or "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": settings.get("model") or "qwen2.5-7b-instruct",
            "messages": self._messages(question, contexts),
            "temperature": float(settings.get("temperature") or 0.2),
        }
        data = self._post_json(f"{base_url}/chat/completions", payload, headers=headers)
        choices = data.get("choices") or []
        if not choices:
            raise LLMError("模型接口未返回 choices。")
        content = choices[0].get("message", {}).get("content")
        if not content:
            raise LLMError("模型接口未返回回答内容。")
        return str(content).strip()

    def _post_json(self, url: str, payload: Dict[str, object], headers: Dict[str, str]) -> Dict[str, object]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", **headers},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise LLMError(f"模型接口调用失败：{exc}") from exc
