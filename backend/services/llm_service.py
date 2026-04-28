from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import Dict, List

from .index_service import Chunk


class LLMError(RuntimeError):
    pass


class LLMClient:
    def generate_answer(
        self,
        question: str,
        context: str,
        sources: List[Dict[str, object]],
        settings: Dict[str, object],
    ) -> str | None:
        if not settings.get("enabled"):
            return None

        base_url = str(settings.get("base_url") or "").rstrip("/")
        if not base_url:
            raise LLMError("请填写模型接口地址。")

        model = str(settings.get("model") or "").strip()
        if not model:
            raise LLMError("请填写模型名称。")

        headers = {}
        api_key = str(settings.get("api_key") or "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model,
            "messages": self._messages(question, context, sources),
            "temperature": float(settings.get("temperature") or 0.2),
        }
        data = self._post_json(
            f"{base_url}/chat/completions",
            payload,
            headers=headers,
            provider_name=str(settings.get("provider_name") or ""),
            model=model,
        )
        choices = data.get("choices") or []
        if not choices:
            raise LLMError("模型接口未返回 choices。")

        content = choices[0].get("message", {}).get("content")
        if not content:
            raise LLMError("模型接口未返回回答内容。")
        return str(content).strip()

    def extractive_answer(self, question: str, contexts: List[Chunk]) -> str:
        if not contexts:
            return "未检索到明确依据。请补充更具体的问题，或先完善制度文档。"

        evidence_blocks = []
        for index, chunk in enumerate(contexts[:3], start=1):
            title_path = " > ".join(chunk.title_path)
            source_line = f"[{index}] {chunk.file_name}"
            if title_path:
                source_line += f" | {title_path}"
            evidence_blocks.append(f"{source_line}\n{chunk.text[:260]}")

        evidence = "\n\n".join(evidence_blocks)
        return (
            "当前未启用大模型生成，以下为向量检索命中的制度依据摘要。\n\n"
            f"{evidence}\n\n"
            "如需更自然、可综合多段依据的回答，请联系管理员在设置中启用模型。"
        )

    def _messages(
        self,
        question: str,
        context: str,
        sources: List[Dict[str, object]],
    ) -> List[Dict[str, str]]:
        source_summary = "\n".join(
            [
                f"[{index}] {item.get('file') or '未知文档'}"
                + (f" | {' > '.join(item.get('title_path') or [])}" if item.get("title_path") else "")
                for index, item in enumerate(sources, start=1)
            ]
        ).strip()

        return [
            {
                "role": "system",
                "content": (
                    "你是企业内部制度问答助手。"
                    "只能基于给定引用片段回答，不要编造制度内容。"
                    "如果片段中没有明确依据，请直接回答“未在现有制度中检索到明确依据”。"
                    "回答要尽量简洁、明确。"
                    "关键结论后请标注引用编号，例如 [1]、[2]。"
                    "如果存在章节路径，请优先结合章节路径辅助说明来源。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"用户问题：{question}\n\n"
                    f"引用目录：\n{source_summary or '无'}\n\n"
                    f"可用引用片段：\n{context or '无'}\n\n"
                    "请只依据以上片段作答。"
                ),
            },
        ]

    def _post_json(
        self,
        url: str,
        payload: Dict[str, object],
        headers: Dict[str, str],
        provider_name: str,
        model: str,
    ) -> Dict[str, object]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", **headers},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise LLMError(self._friendly_error(provider_name, model, detail or str(exc))) from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise LLMError("模型请求超过 20 秒，已回退本地摘要。") from exc
            if provider_name == "ollama":
                raise LLMError("未能连接到 Ollama，请确认已安装并启动 Ollama。") from exc
            raise LLMError(f"模型接口调用失败：{exc}") from exc
        except TimeoutError as exc:
            raise LLMError("模型请求超过 20 秒，已回退本地摘要。") from exc
        except socket.timeout as exc:
            raise LLMError("模型请求超过 20 秒，已回退本地摘要。") from exc

    def _friendly_error(self, provider_name: str, model: str, detail: str) -> str:
        lowered = detail.lower()
        if provider_name == "ollama":
            if "not found" in lowered or "model" in lowered:
                return f"Ollama 模型 {model} 不可用，请先执行 ollama pull {model}。"
            return f"Ollama 调用失败：{detail}"
        return f"模型接口调用失败：{detail}"
