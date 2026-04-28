from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Dict


MODEL_KEYS = ("gpt", "deepseek", "qwen", "ollama")
MASKED_SECRET = "********"

DEFAULT_MODEL_SETTINGS: Dict[str, Dict[str, object]] = {
    "gpt": {
        "provider_name": "gpt",
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-4o-mini",
        "enabled": False,
    },
    "deepseek": {
        "provider_name": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "",
        "model": "deepseek-chat",
        "enabled": False,
    },
    "qwen": {
        "provider_name": "qwen",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": "",
        "model": "qwen-plus",
        "enabled": False,
    },
    "ollama": {
        "provider_name": "ollama",
        "base_url": "http://127.0.0.1:11434/v1",
        "api_key": "ollama",
        "model": "qwen2.5:3b",
        "enabled": False,
    },
}

DEFAULT_EMBEDDING_SETTINGS: Dict[str, object] = {
    "provider": "qwen",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "api_key": "",
    "model": "text-embedding-v4",
    "enabled": False,
}

DEFAULT_SETTINGS: Dict[str, object] = {
    "models": deepcopy(DEFAULT_MODEL_SETTINGS),
    "embedding": deepcopy(DEFAULT_EMBEDDING_SETTINGS),
    "temperature": 0.2,
    "top_k": 3,
    "max_context_sources": 3,
    "max_snippet_chars": 500,
    "max_context_chars": 1500,
}


class SettingsService:
    def __init__(self, settings_path: Path):
        self.settings_path = settings_path

    def load(self, mask_secret: bool = True) -> Dict[str, object]:
        stored = self._load_raw()
        normalized = self._normalize(stored)
        payload = self._with_active_fields(normalized)
        return self._mask(payload) if mask_secret else payload

    def save(self, payload: Dict[str, object]) -> Dict[str, object]:
        current = self.load(mask_secret=False)
        incoming = dict(payload)
        merged = {
            "models": self._merge_models(current["models"], incoming),
            "embedding": self._merge_embedding(current["embedding"], incoming.get("embedding")),
            "temperature": incoming.get("temperature", current.get("temperature")),
            "top_k": incoming.get(
                "max_context_sources",
                incoming.get("top_k", current.get("max_context_sources", current.get("top_k"))),
            ),
            "max_context_sources": incoming.get(
                "max_context_sources",
                incoming.get("top_k", current.get("max_context_sources", current.get("top_k"))),
            ),
            "max_snippet_chars": incoming.get("max_snippet_chars", current.get("max_snippet_chars")),
            "max_context_chars": incoming.get("max_context_chars", current.get("max_context_chars")),
        }
        normalized = self._normalize(merged)
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self._mask(self._with_active_fields(normalized))

    def _load_raw(self) -> Dict[str, object]:
        if not self.settings_path.exists():
            return {}
        try:
            payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _normalize(self, settings: Dict[str, object]) -> Dict[str, object]:
        normalized = {
            "models": deepcopy(DEFAULT_MODEL_SETTINGS),
            "embedding": deepcopy(DEFAULT_EMBEDDING_SETTINGS),
            "temperature": DEFAULT_SETTINGS["temperature"],
            "top_k": DEFAULT_SETTINGS["top_k"],
            "max_context_sources": DEFAULT_SETTINGS["max_context_sources"],
            "max_snippet_chars": DEFAULT_SETTINGS["max_snippet_chars"],
            "max_context_chars": DEFAULT_SETTINGS["max_context_chars"],
        }

        incoming_models = self._extract_model_payload(settings)
        for model_key, defaults in DEFAULT_MODEL_SETTINGS.items():
            raw = incoming_models.get(model_key, {})
            item = dict(defaults)
            if isinstance(raw, dict):
                item.update(raw)

            item["provider_name"] = str(item.get("provider_name") or model_key)
            item["base_url"] = str(item.get("base_url") or "").rstrip("/")
            item["api_key"] = str(item.get("api_key") or "")
            item["model"] = str(item.get("model") or defaults["model"])
            item["enabled"] = bool(item.get("enabled"))
            normalized["models"][model_key] = item

        enabled_models = [key for key, item in normalized["models"].items() if item["enabled"]]
        if len(enabled_models) > 1:
            raise ValueError("最多只能启用一个回答模型。")

        embedding_raw = settings.get("embedding")
        embedding = dict(DEFAULT_EMBEDDING_SETTINGS)
        if isinstance(embedding_raw, dict):
            embedding.update(embedding_raw)

        embedding["provider"] = str(embedding.get("provider") or DEFAULT_EMBEDDING_SETTINGS["provider"]).strip()
        embedding["base_url"] = str(embedding.get("base_url") or "").rstrip("/")
        embedding["api_key"] = str(embedding.get("api_key") or "")
        embedding["model"] = str(embedding.get("model") or DEFAULT_EMBEDDING_SETTINGS["model"]).strip()
        embedding["enabled"] = bool(embedding.get("enabled"))
        normalized["embedding"] = embedding

        try:
            normalized["temperature"] = max(0.0, min(float(settings.get("temperature", 0.2)), 2.0))
        except (TypeError, ValueError):
            normalized["temperature"] = DEFAULT_SETTINGS["temperature"]

        source_limit_raw = settings.get("max_context_sources", settings.get("top_k", 3))
        try:
            source_limit = max(1, min(int(source_limit_raw), 10))
        except (TypeError, ValueError):
            source_limit = DEFAULT_SETTINGS["max_context_sources"]
        normalized["top_k"] = source_limit
        normalized["max_context_sources"] = source_limit

        try:
            normalized["max_snippet_chars"] = max(100, min(int(settings.get("max_snippet_chars", 500)), 2000))
        except (TypeError, ValueError):
            normalized["max_snippet_chars"] = DEFAULT_SETTINGS["max_snippet_chars"]

        try:
            normalized["max_context_chars"] = max(300, min(int(settings.get("max_context_chars", 1500)), 5000))
        except (TypeError, ValueError):
            normalized["max_context_chars"] = DEFAULT_SETTINGS["max_context_chars"]

        return normalized

    def _extract_model_payload(self, settings: Dict[str, object]) -> Dict[str, Dict[str, object]]:
        incoming_models = settings.get("models")
        if isinstance(incoming_models, dict):
            models = {
                key: value
                for key, value in incoming_models.items()
                if key in MODEL_KEYS and isinstance(value, dict)
            }
            if models:
                return models

        legacy_provider = str(settings.get("provider") or "").strip()
        if not legacy_provider and not any(
            key in settings for key in ("enabled", "base_url", "api_key", "model")
        ):
            return {}

        if legacy_provider == "ollama":
            model_key = "ollama"
        elif legacy_provider in MODEL_KEYS:
            model_key = legacy_provider
        else:
            model_key = "gpt"

        return {
            model_key: {
                "provider_name": model_key,
                "base_url": settings.get("base_url"),
                "api_key": settings.get("api_key"),
                "model": settings.get("model"),
                "enabled": settings.get("enabled"),
            }
        }

    def _merge_models(
        self,
        current_models: Dict[str, Dict[str, object]],
        incoming: Dict[str, object],
    ) -> Dict[str, Dict[str, object]]:
        merged = deepcopy(current_models)
        for model_key, config in self._extract_model_payload(incoming).items():
            current_item = dict(merged.get(model_key) or DEFAULT_MODEL_SETTINGS[model_key])
            next_item = dict(current_item)
            for field in ("provider_name", "base_url", "model", "enabled"):
                if field in config:
                    next_item[field] = config[field]
            if "api_key" in config and config["api_key"] != MASKED_SECRET:
                next_item["api_key"] = config["api_key"]
            merged[model_key] = next_item
        return merged

    def _merge_embedding(
        self,
        current_embedding: Dict[str, object],
        incoming_embedding: object,
    ) -> Dict[str, object]:
        merged = deepcopy(current_embedding)
        if not isinstance(incoming_embedding, dict):
            return merged

        for field in ("provider", "base_url", "model", "enabled"):
            if field in incoming_embedding:
                merged[field] = incoming_embedding[field]
        if "api_key" in incoming_embedding and incoming_embedding["api_key"] != MASKED_SECRET:
            merged["api_key"] = incoming_embedding["api_key"]
        return merged

    def _with_active_fields(self, settings: Dict[str, object]) -> Dict[str, object]:
        payload = deepcopy(settings)
        active_mode = self._get_active_mode(payload["models"])
        payload["active_mode"] = active_mode

        active_model = payload["models"].get(active_mode) if active_mode in payload["models"] else None
        if active_model:
            payload["enabled"] = True
            payload["provider"] = "ollama" if active_mode == "ollama" else "openai_compatible"
            payload["provider_name"] = active_model["provider_name"]
            payload["base_url"] = active_model["base_url"]
            payload["api_key"] = active_model["api_key"]
            payload["model"] = active_model["model"]
        else:
            payload["enabled"] = False
            payload["provider"] = "ollama"
            payload["provider_name"] = "extractive"
            payload["base_url"] = DEFAULT_MODEL_SETTINGS["ollama"]["base_url"]
            payload["api_key"] = ""
            payload["model"] = DEFAULT_MODEL_SETTINGS["ollama"]["model"]

        return payload

    def _get_active_mode(self, models: Dict[str, Dict[str, object]]) -> str:
        for model_key in MODEL_KEYS:
            item = models.get(model_key) or {}
            if item.get("enabled"):
                return model_key
        return "extractive"

    def _mask(self, settings: Dict[str, object]) -> Dict[str, object]:
        masked = deepcopy(settings)
        for item in masked.get("models", {}).values():
            if item.get("api_key"):
                item["api_key"] = MASKED_SECRET
        embedding = masked.get("embedding") or {}
        if embedding.get("api_key"):
            embedding["api_key"] = MASKED_SECRET
        if masked.get("api_key"):
            masked["api_key"] = MASKED_SECRET
        return masked
