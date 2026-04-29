from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


class HistoryService:
    """历史服务：记录用户问答行为并支持查询与手机号迁移。"""
    def __init__(self, history_path: Path):
        self.history_path = history_path

    def add_entry(self, phone: str, question: str, answer: str, source_count: int) -> Dict[str, object]:
        """保存一条问答历史，限制答案长度以减少存储量。"""
        store = self._load_store()
        item = {
            "id": uuid.uuid4().hex,
            "phone": phone,
            "question": question,
            "answer": answer[:500],
            "source_count": source_count,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        store.append(item)
        self._save_store(store)
        return item

    def list_entries(self, phone: str, limit: int = 30) -> List[Dict[str, object]]:
        store = self._load_store()
        items = [item for item in store if item.get("phone") == phone]
        items.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return items[:limit]

    def migrate_phone(self, old_phone: str, new_phone: str) -> None:
        store = self._load_store()
        changed = False
        for item in store:
            if item.get("phone") == old_phone:
                item["phone"] = new_phone
                changed = True
        if changed:
            self._save_store(store)

    def _load_store(self) -> List[Dict[str, object]]:
        if not self.history_path.exists():
            return []
        try:
            payload = json.loads(self.history_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        items = payload.get("items", []) if isinstance(payload, dict) else []
        return [item for item in items if isinstance(item, dict)]

    def _save_store(self, items: List[Dict[str, object]]) -> None:
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_path.write_text(
            json.dumps({"items": items}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
