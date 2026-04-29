from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.error
import urllib.request
from typing import Dict, List


DEFAULT_EMBEDDING_PROVIDER = "qwen"
DEFAULT_EMBEDDING_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_EMBEDDING_MODEL = "text-embedding-v4"
LOCAL_FALLBACK_MODEL = "local_hash_fallback"


class BaseEmbeddingBackend:
    """Embedding 后端基类：约定 provider_name、model_name 和 quality 属性。"""
    provider_name = "base"
    model_name = "base"
    quality = "fallback"

    def embed(self, text: str) -> List[float]:
        raise NotImplementedError

    def similarity(self, left: List[float], right: List[float]) -> float:
        if not left or not right:
            return 0.0
        return sum(a * b for a, b in zip(left, right))


class LocalHashEmbeddingBackend(BaseEmbeddingBackend):
    """本地哈希 Embedding：用于低成本 fallback 向量生成，适合没有真实 Embedding 配置时使用。"""
    provider_name = "local_hash"
    model_name = LOCAL_FALLBACK_MODEL
    quality = "fallback"

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    def embed(self, text: str) -> List[float]:
        vector = [0.0] * self.dimensions
        for token in self._features(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign

        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0:
            return vector
        return [v / norm for v in vector]

    def _features(self, text: str) -> List[str]:
        normalized = text.lower().strip()
        zh_segments = re.findall(r"[\u4e00-\u9fff]+", normalized)
        en_tokens = re.findall(r"[a-z0-9_\-/]+", normalized)

        features: List[str] = []
        for segment in zh_segments:
            features.append(segment)
            if len(segment) > 1:
                features.extend(segment[i : i + 2] for i in range(len(segment) - 1))
                features.extend(segment[i : i + 3] for i in range(len(segment) - 2))

        features.extend(en_tokens)
        return features


class OpenAICompatibleEmbeddingBackend(BaseEmbeddingBackend):
    """兼容 OpenAI API 的 Embedding 后端：支持云端真实 Embedding 计算。"""
    provider_name = "openai_compatible"
    quality = "real"

    def __init__(self, provider_name: str, base_url: str, api_key: str, model: str):
        self.provider_name = str(provider_name or "openai_compatible").strip().lower()
        self.base_url = str(base_url or "").rstrip("/")
        self.api_key = str(api_key or "")
        self.model_name = str(model or "").strip()

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model_name)

    def embed(self, text: str) -> List[float]:
        if not self.is_configured():
            raise ValueError("真实 Embedding 未完整配置。")

        payload = {"model": self.model_name, "input": text}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = self._post_json(f"{self.base_url}/embeddings", payload, headers)
        items = data.get("data") or []
        if not items:
            raise ValueError("Embedding 接口未返回 data。")
        vector = items[0].get("embedding") or []
        if not vector:
            raise ValueError("Embedding 接口未返回 embedding。")
        return [float(item) for item in vector]

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
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ValueError(f"真实 Embedding 调用失败：{detail or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise ValueError(f"真实 Embedding 调用失败：{exc}") from exc


class EmbeddingService:
    """Embedding 服务：根据配置选择真实 Embedding 或本地回退 Embedding，并返回向量。"""
    def __init__(
        self,
        provider_name: str = "",
        base_url: str = "",
        api_key: str = "",
        model: str = "",
        enabled: bool = False,
        dimensions: int = 384,
    ):
        self.dimensions = dimensions
        self.fallback_backend = LocalHashEmbeddingBackend(dimensions=dimensions)
        self._configured_provider_name = str(provider_name or "").strip().lower()
        self._configured_base_url = str(base_url or "").strip()
        self._configured_api_key = str(api_key or "").strip()
        self._configured_model = str(model or "").strip()
        self._configured_enabled = bool(enabled)

        self._backend: BaseEmbeddingBackend | None = None
        self.provider_name = self.fallback_backend.provider_name
        self.model_name = self.fallback_backend.model_name
        self.embedding_quality = self.fallback_backend.quality
        self.fallback_reason: str | None = None

        if self._configured_provider_name == "local_hash":
            self._backend = self.fallback_backend

    @classmethod
    def from_settings(cls, embedding_settings: Dict[str, object] | None) -> "EmbeddingService":
        config = embedding_settings or {}
        return cls(
            provider_name=str(config.get("provider") or DEFAULT_EMBEDDING_PROVIDER),
            base_url=str(config.get("base_url") or DEFAULT_EMBEDDING_BASE_URL),
            api_key=str(config.get("api_key") or ""),
            model=str(config.get("model") or DEFAULT_EMBEDDING_MODEL),
            enabled=bool(config.get("enabled")),
        )

    @classmethod
    def low_memory_default(cls) -> "EmbeddingService":
        return cls(provider_name="local_hash", enabled=False)

    def embed(self, text: str) -> List[float]:
        if self._backend is not None:
            return self._embed_with_backend(self._backend, text)

        if self._should_use_real_embedding():
            backend = OpenAICompatibleEmbeddingBackend(
                provider_name=self._configured_provider_name,
                base_url=self._configured_base_url,
                api_key=self._configured_api_key,
                model=self._configured_model,
            )
            try:
                return self._embed_with_backend(backend, text)
            except ValueError as exc:
                self._switch_to_fallback(str(exc))
                return self._embed_with_backend(self.fallback_backend, text)

        self._switch_to_fallback(self._fallback_reason_for_configuration())
        return self._embed_with_backend(self.fallback_backend, text)

    def similarity(self, left: List[float], right: List[float]) -> float:
        return self.fallback_backend.similarity(left, right)

    def describe(self) -> Dict[str, object]:
        return {
            "embedding_provider": self.provider_name,
            "embedding_model": self.model_name,
            "embedding_quality": self.embedding_quality,
            "fallback_reason": self.fallback_reason,
        }

    def is_real_enabled_and_configured(self) -> bool:
        return self._should_use_real_embedding()

    def _embed_with_backend(self, backend: BaseEmbeddingBackend, text: str) -> List[float]:
        vector = backend.embed(text)
        self._backend = backend
        self.provider_name = backend.provider_name
        self.model_name = backend.model_name
        self.embedding_quality = backend.quality
        return vector

    def _should_use_real_embedding(self) -> bool:
        return self._configured_enabled and bool(
            self._configured_provider_name
            and self._configured_base_url
            and self._configured_api_key
            and self._configured_model
            and self._configured_provider_name != "local_hash"
        )

    def _fallback_reason_for_configuration(self) -> str | None:
        if self._configured_provider_name == "local_hash":
            return None
        if not self._configured_enabled:
            return "未启用真实 Embedding，已回退本地 fallback embedding。"
        if not self._configured_api_key:
            return "未配置 Embedding API Key，已回退本地 fallback embedding。"
        if not self._configured_base_url or not self._configured_model:
            return "Embedding 配置不完整，已回退本地 fallback embedding。"
        return "真实 Embedding 当前不可用，已回退本地 fallback embedding。"

    def _switch_to_fallback(self, reason: str | None) -> None:
        self._backend = self.fallback_backend
        self.provider_name = self.fallback_backend.provider_name
        self.model_name = self.fallback_backend.model_name
        self.embedding_quality = self.fallback_backend.quality
        self.fallback_reason = reason


class LocalEmbeddingService(EmbeddingService):
    def __init__(self, dimensions: int = 384):
        super().__init__(provider_name="local_hash", enabled=False, dimensions=dimensions)
