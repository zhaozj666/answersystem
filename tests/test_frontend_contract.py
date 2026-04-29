from __future__ import annotations

import re
import unittest
from pathlib import Path


class FrontendDomContractTest(unittest.TestCase):
    def test_all_js_element_ids_exist_in_html(self) -> None:
        root = Path(__file__).resolve().parent.parent
        html = (root / "frontend" / "index.html").read_text(encoding="utf-8")
        js = (root / "frontend" / "js" / "app.js").read_text(encoding="utf-8")

        ids_in_js = re.findall(r'getElementById\("([^"]+)"\)', js)
        missing = sorted({element_id for element_id in ids_in_js if f'id="{element_id}"' not in html})

        self.assertEqual(missing, [], f"missing DOM ids referenced by app.js: {missing}")


if __name__ == "__main__":
    unittest.main()
