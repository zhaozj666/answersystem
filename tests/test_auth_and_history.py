from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.app import create_app
from backend.services.auth_service import AuthService
from backend.services.history_service import HistoryService


class AuthServiceTest(unittest.TestCase):
    def test_bootstraps_admin_account(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            auth = AuthService(Path(tmp) / "accounts.json")

            account = auth.authenticate("15100000000", "123456")

            self.assertIsNotNone(account)
            self.assertEqual(account["role"], "admin")

    def test_history_is_isolated_by_phone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            history = HistoryService(Path(tmp) / "history.json")

            history.add_entry("15100000000", "管理员问题", "管理员回答", 3)
            history.add_entry("13900000000", "普通用户问题", "普通用户回答", 1)

            admin_entries = history.list_entries("15100000000")
            user_entries = history.list_entries("13900000000")

            self.assertEqual(len(admin_entries), 1)
            self.assertEqual(admin_entries[0]["question"], "管理员问题")
            self.assertEqual(len(user_entries), 1)
            self.assertEqual(user_entries[0]["question"], "普通用户问题")


class AppAuthFlowTest(unittest.TestCase):
    def test_settings_requires_admin_role(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(
                base_dir=Path(tmp),
                docs_dir=Path(tmp) / "docs",
                settings_path=Path(tmp) / "runtime" / "model_settings.json",
                accounts_path=Path(tmp) / "runtime" / "accounts.json",
                history_path=Path(tmp) / "runtime" / "history.json",
                testing=True,
            )
            client = app.test_client()

            login_res = client.post(
                "/api/auth/login",
                json={"phone": "15100000000", "password": "123456"},
            )
            self.assertEqual(login_res.status_code, 200)

            settings_res = client.get("/api/settings")
            self.assertEqual(settings_res.status_code, 200)

            client.post(
                "/api/admin/accounts",
                json={"phone": "13900000000", "password": "123456", "role": "user"},
            )
            client.post("/api/auth/logout")
            client.post(
                "/api/auth/login",
                json={"phone": "13900000000", "password": "123456"},
            )

            forbidden_res = client.get("/api/settings")
            self.assertEqual(forbidden_res.status_code, 403)

    def test_ask_requires_login_and_writes_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp) / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)
            (docs_dir / "policy.md").write_text(
                "正式员工指与公司签订劳动合同的全日制员工。",
                encoding="utf-8",
            )

            app = create_app(
                base_dir=Path(tmp),
                docs_dir=docs_dir,
                settings_path=Path(tmp) / "runtime" / "model_settings.json",
                accounts_path=Path(tmp) / "runtime" / "accounts.json",
                history_path=Path(tmp) / "runtime" / "history.json",
                testing=True,
            )
            app.index_service.reindex()
            client = app.test_client()

            unauth_res = client.post("/api/ask", json={"question": "什么是正式员工？"})
            self.assertEqual(unauth_res.status_code, 401)

            client.post(
                "/api/auth/login",
                json={"phone": "15100000000", "password": "123456"},
            )
            ask_res = client.post("/api/ask", json={"question": "什么是正式员工？"})
            self.assertEqual(ask_res.status_code, 200)

            history_res = client.get("/api/history")
            self.assertEqual(history_res.status_code, 200)
            history_data = history_res.get_json()
            self.assertEqual(len(history_data["items"]), 1)
            self.assertEqual(history_data["items"][0]["question"], "什么是正式员工？")


if __name__ == "__main__":
    unittest.main()
