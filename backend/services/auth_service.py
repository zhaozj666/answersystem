from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from werkzeug.security import check_password_hash, generate_password_hash


class AuthError(ValueError):
    pass


class AuthService:
    def __init__(
        self,
        accounts_path: Path,
        admin_phone: str = "15100000000",
        admin_password: str = "123456",
    ):
        self.accounts_path = accounts_path
        self.admin_phone = admin_phone
        self.admin_password = admin_password
        self._ensure_bootstrap()

    def authenticate(self, phone: str, password: str) -> Optional[Dict[str, object]]:
        account = self._find_account(phone)
        if not account:
            return None
        if not check_password_hash(str(account["password_hash"]), password):
            return None
        return self._public_account(account)

    def get_account(self, phone: str) -> Optional[Dict[str, object]]:
        account = self._find_account(phone)
        return self._public_account(account) if account else None

    def verify_password(self, phone: str, password: str) -> bool:
        account = self._find_account(phone)
        return bool(account and check_password_hash(str(account["password_hash"]), password))

    def list_accounts(self) -> List[Dict[str, object]]:
        accounts = self._load_accounts()
        return [self._public_account(item) for item in accounts]

    def create_account(self, phone: str, password: str, role: str = "user") -> Dict[str, object]:
        normalized_phone = self._normalize_phone(phone)
        self._validate_password(password)

        accounts = self._load_accounts()
        if any(item["phone"] == normalized_phone for item in accounts):
            raise AuthError("该手机号已存在。")

        account = {
            "phone": normalized_phone,
            "role": "admin" if role == "admin" else "user",
            "password_hash": generate_password_hash(password),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        accounts.append(account)
        self._save_accounts(accounts)
        return self._public_account(account)

    def update_profile(self, current_phone: str, new_phone: str) -> Dict[str, object]:
        normalized_phone = self._normalize_phone(new_phone)
        accounts = self._load_accounts()
        current = None
        for item in accounts:
            if item["phone"] == current_phone:
                current = item
                continue
            if item["phone"] == normalized_phone:
                raise AuthError("新手机号已被占用。")

        if not current:
            raise AuthError("账号不存在。")

        current["phone"] = normalized_phone
        self._save_accounts(accounts)
        return self._public_account(current)

    def update_password(self, phone: str, new_password: str) -> Dict[str, object]:
        self._validate_password(new_password)
        accounts = self._load_accounts()
        for item in accounts:
            if item["phone"] == phone:
                item["password_hash"] = generate_password_hash(new_password)
                self._save_accounts(accounts)
                return self._public_account(item)
        raise AuthError("账号不存在。")

    def _ensure_bootstrap(self) -> None:
        accounts = self._load_accounts()
        if any(item.get("role") == "admin" and item.get("phone") == self.admin_phone for item in accounts):
            return

        accounts.append(
            {
                "phone": self.admin_phone,
                "role": "admin",
                "password_hash": generate_password_hash(self.admin_password),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self._save_accounts(accounts)

    def _find_account(self, phone: str) -> Optional[Dict[str, object]]:
        normalized_phone = self._normalize_phone(phone)
        for item in self._load_accounts():
            if item["phone"] == normalized_phone:
                return item
        return None

    def _load_accounts(self) -> List[Dict[str, object]]:
        if not self.accounts_path.exists():
            return []
        try:
            payload = json.loads(self.accounts_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        items = payload.get("accounts", []) if isinstance(payload, dict) else []
        return [item for item in items if isinstance(item, dict)]

    def _save_accounts(self, accounts: List[Dict[str, object]]) -> None:
        self.accounts_path.parent.mkdir(parents=True, exist_ok=True)
        self.accounts_path.write_text(
            json.dumps({"accounts": accounts}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _normalize_phone(self, phone: str) -> str:
        value = str(phone or "").strip()
        if len(value) != 11 or not value.isdigit():
            raise AuthError("手机号必须是 11 位数字。")
        return value

    def _validate_password(self, password: str) -> None:
        value = str(password or "")
        if len(value) < 6:
            raise AuthError("密码长度不能少于 6 位。")

    def _public_account(self, account: Dict[str, object]) -> Dict[str, object]:
        return {
            "phone": account["phone"],
            "role": account["role"],
            "created_at": account.get("created_at"),
        }
