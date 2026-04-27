from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.services.settings_service import SettingsService


class SettingsServiceTest(unittest.TestCase):
    def test_saves_settings_and_masks_api_key_for_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = SettingsService(Path(tmp) / "settings.json")

            saved = service.save(
                {
                    "enabled": True,
                    "provider": "openai_compatible",
                    "base_url": "https://example.com/v1",
                    "api_key": "secret-token",
                    "model": "free-model",
                    "temperature": 0.1,
                }
            )

            self.assertEqual(saved["api_key"], "********")
            loaded = service.load(mask_secret=False)
            self.assertEqual(loaded["api_key"], "secret-token")
            self.assertEqual(loaded["model"], "free-model")


if __name__ == "__main__":
    unittest.main()
