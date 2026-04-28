from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.app import create_app
from backend.services.settings_service import SettingsService


class SettingsServiceTest(unittest.TestCase):
    def test_defaults_include_independent_embedding_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = SettingsService(Path(tmp) / "settings.json")

            loaded = service.load(mask_secret=False)

            self.assertEqual(loaded["embedding"]["provider"], "qwen")
            self.assertEqual(
                loaded["embedding"]["base_url"],
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
            self.assertEqual(loaded["embedding"]["model"], "text-embedding-v4")
            self.assertEqual(loaded["embedding"]["enabled"], False)
            self.assertEqual(loaded["embedding"]["api_key"], "")
            self.assertEqual(loaded["top_k"], 3)
            self.assertEqual(loaded["max_context_sources"], 3)
            self.assertEqual(loaded["max_snippet_chars"], 500)
            self.assertEqual(loaded["max_context_chars"], 1500)

    def test_saves_multi_model_settings_and_masks_api_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = SettingsService(Path(tmp) / "settings.json")

            saved = service.save(
                {
                    "models": {
                        "gpt": {
                            "provider_name": "gpt",
                            "base_url": "https://api.openai.com/v1/",
                            "api_key": "secret-token",
                            "model": "gpt-4o-mini",
                            "enabled": True,
                        }
                    },
                    "temperature": 0.1,
                }
            )

            self.assertEqual(saved["models"]["gpt"]["api_key"], "********")
            self.assertEqual(saved["active_mode"], "gpt")
            loaded = service.load(mask_secret=False)
            self.assertEqual(loaded["models"]["gpt"]["api_key"], "secret-token")
            self.assertEqual(loaded["models"]["gpt"]["base_url"], "https://api.openai.com/v1")
            self.assertEqual(loaded["models"]["gpt"]["model"], "gpt-4o-mini")

    def test_saves_embedding_config_and_masks_embedding_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = SettingsService(Path(tmp) / "settings.json")

            saved = service.save(
                {
                    "embedding": {
                        "provider": "qwen",
                        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/",
                        "api_key": "embed-secret",
                        "model": "text-embedding-v4",
                        "enabled": True,
                    }
                }
            )

            self.assertEqual(saved["embedding"]["api_key"], "********")
            loaded = service.load(mask_secret=False)
            self.assertEqual(loaded["embedding"]["api_key"], "embed-secret")
            self.assertEqual(
                loaded["embedding"]["base_url"],
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
            self.assertEqual(loaded["embedding"]["enabled"], True)

    def test_saves_retrieval_and_context_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = SettingsService(Path(tmp) / "settings.json")

            saved = service.save(
                {
                    "max_context_sources": 2,
                    "max_snippet_chars": 320,
                    "max_context_chars": 900,
                }
            )

            self.assertEqual(saved["top_k"], 2)
            self.assertEqual(saved["max_context_sources"], 2)
            self.assertEqual(saved["max_snippet_chars"], 320)
            self.assertEqual(saved["max_context_chars"], 900)

            loaded = service.load(mask_secret=False)
            self.assertEqual(loaded["top_k"], 2)
            self.assertEqual(loaded["max_context_sources"], 2)
            self.assertEqual(loaded["max_snippet_chars"], 320)
            self.assertEqual(loaded["max_context_chars"], 900)

    def test_top_k_follows_max_context_sources_for_compatibility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = SettingsService(Path(tmp) / "settings.json")

            saved = service.save({"top_k": 4})

            self.assertEqual(saved["top_k"], 4)
            self.assertEqual(saved["max_context_sources"], 4)

    def test_keeps_existing_api_key_when_mask_value_is_posted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = SettingsService(Path(tmp) / "settings.json")

            service.save(
                {
                    "models": {
                        "deepseek": {
                            "provider_name": "deepseek",
                            "base_url": "https://api.deepseek.com/v1",
                            "api_key": "existing-secret",
                            "model": "deepseek-chat",
                            "enabled": True,
                        }
                    }
                }
            )

            service.save(
                {
                    "models": {
                        "deepseek": {
                            "provider_name": "deepseek",
                            "base_url": "https://api.deepseek.com/v1/",
                            "api_key": "********",
                            "model": "deepseek-chat",
                            "enabled": True,
                        }
                    }
                }
            )

            loaded = service.load(mask_secret=False)
            self.assertEqual(loaded["models"]["deepseek"]["api_key"], "existing-secret")
            self.assertEqual(loaded["models"]["deepseek"]["base_url"], "https://api.deepseek.com/v1")

    def test_keeps_existing_embedding_api_key_when_mask_value_is_posted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = SettingsService(Path(tmp) / "settings.json")

            service.save(
                {
                    "embedding": {
                        "provider": "openai_compatible",
                        "base_url": "https://api.openai.com/v1",
                        "api_key": "embed-existing-secret",
                        "model": "text-embedding-3-small",
                        "enabled": True,
                    }
                }
            )

            service.save(
                {
                    "embedding": {
                        "provider": "openai_compatible",
                        "base_url": "https://api.openai.com/v1/",
                        "api_key": "********",
                        "model": "text-embedding-3-small",
                        "enabled": True,
                    }
                }
            )

            loaded = service.load(mask_secret=False)
            self.assertEqual(loaded["embedding"]["api_key"], "embed-existing-secret")
            self.assertEqual(loaded["embedding"]["base_url"], "https://api.openai.com/v1")

    def test_returns_extractive_when_no_model_is_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = SettingsService(Path(tmp) / "settings.json")

            loaded = service.load(mask_secret=False)

            self.assertEqual(loaded["active_mode"], "extractive")

    def test_rejects_multiple_enabled_models(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = SettingsService(Path(tmp) / "settings.json")

            with self.assertRaises(ValueError):
                service.save(
                    {
                        "models": {
                            "gpt": {
                                "provider_name": "gpt",
                                "base_url": "https://api.openai.com/v1",
                                "api_key": "one",
                                "model": "gpt-4o-mini",
                                "enabled": True,
                            },
                            "qwen": {
                                "provider_name": "qwen",
                                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                                "api_key": "two",
                                "model": "qwen-plus",
                                "enabled": True,
                            },
                        }
                    }
                )


class SettingsApiTest(unittest.TestCase):
    def test_settings_api_returns_masked_multi_model_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(
                base_dir=Path(tmp),
                docs_dir=Path(tmp) / "docs",
                settings_path=Path(tmp) / "runtime" / "model_settings.json",
                accounts_path=Path(tmp) / "runtime" / "accounts.json",
                history_path=Path(tmp) / "runtime" / "history.json",
                testing=True,
            )
            app.settings_service.save(
                {
                    "models": {
                        "gpt": {
                            "provider_name": "gpt",
                            "base_url": "https://api.openai.com/v1",
                            "api_key": "secret-token",
                            "model": "gpt-4o-mini",
                            "enabled": True,
                        }
                    }
                }
            )
            client = app.test_client()
            client.post("/api/auth/login", json={"phone": "15100000000", "password": "123456"})

            response = client.get("/api/settings")

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data["models"]["gpt"]["api_key"], "********")
            self.assertEqual(data["embedding"]["api_key"], "")
            self.assertEqual(data["active_mode"], "gpt")

    def test_settings_api_saves_multi_model_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "runtime" / "model_settings.json"
            app = create_app(
                base_dir=Path(tmp),
                docs_dir=Path(tmp) / "docs",
                settings_path=settings_path,
                accounts_path=Path(tmp) / "runtime" / "accounts.json",
                history_path=Path(tmp) / "runtime" / "history.json",
                testing=True,
            )
            client = app.test_client()
            client.post("/api/auth/login", json={"phone": "15100000000", "password": "123456"})

            response = client.post(
                "/api/settings",
                json={
                    "models": {
                        "ollama": {
                            "provider_name": "ollama",
                            "base_url": "http://127.0.0.1:11434/v1/",
                            "api_key": "ollama",
                            "model": "qwen2.5:3b",
                            "enabled": True,
                        }
                    }
                },
            )

            self.assertEqual(response.status_code, 200)
            stored = app.settings_service.load(mask_secret=False)
            self.assertEqual(stored["models"]["ollama"]["base_url"], "http://127.0.0.1:11434/v1")
            self.assertEqual(stored["active_mode"], "ollama")

    def test_default_ollama_model_uses_low_memory_variant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = SettingsService(Path(tmp) / "settings.json")

            loaded = service.load(mask_secret=False)

            self.assertEqual(loaded["models"]["ollama"]["model"], "qwen2.5:3b")


if __name__ == "__main__":
    unittest.main()
