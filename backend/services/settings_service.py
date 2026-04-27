from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


DEFAULT_SETTINGS: Dict[str, object] = {
    "enabled": False,
    "provider": "ollama",
    "base_url": "http://127.0.0.1:11434",
    "api_key": "",
    "model": "qwen2.5:7b",
    "temperature": 0.2,
    "top_k": 5,
}


class SettingsService:
    def __init__(self, settings_path: Path):
        self.settings_path = settings_path

    def load(self, mask_secret: bool = True) -> Dict[str, object]:
        settings = dict(DEFAULT_SETTINGS)
        if self.settings_path.exists():
            try:
                stored = json.loads(self.settings_path.read_text(encoding="utf-8"))
                if isinstance(stored, dict):
                    settings.update(stored)
            except json.JSONDecodeError:
                pass
        return self._mask(settings) if mask_secret else settings

    def save(self, payload: Dict[str, object]) -> Dict[str, object]:
        current = self.load(mask_secret=False)
        incoming = dict(payload)
        if incoming.get("api_key") == "********":
            incoming.pop("api_key", None)

        merged = self._normalize({**current, **incoming})
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        return self._mask(merged)

    def _normalize(self, settings: Dict[str, object]) -> Dict[str, object]:
        normalized = dict(DEFAULT_SETTINGS)
        normalized.update(settings)

        normalized["enabled"] = bool(normalized.get("enabled"))
        normalized["provider"] = str(normalized.get("provider") or DEFAULT_SETTINGS["provider"])
        normalized["base_url"] = str(normalized.get("base_url") or "").rstrip("/")
        normalized["api_key"] = str(normalized.get("api_key") or "")
        normalized["model"] = str(normalized.get("model") or DEFAULT_SETTINGS["model"])

        try:
            normalized["temperature"] = max(0.0, min(float(normalized.get("temperature", 0.2)), 2.0))
        except (TypeError, ValueError):
            normalized["temperature"] = DEFAULT_SETTINGS["temperature"]

        try:
            normalized["top_k"] = max(1, min(int(normalized.get("top_k", 5)), 10))
        except (TypeError, ValueError):
            normalized["top_k"] = DEFAULT_SETTINGS["top_k"]

        return normalized

    def _mask(self, settings: Dict[str, object]) -> Dict[str, object]:
        masked = dict(settings)
        if masked.get("api_key"):
            masked["api_key"] = "********"
        return masked
