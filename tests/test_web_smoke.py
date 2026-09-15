"""Optional Gradio UI smoke tests.

The tests are skipped when the full web dependency stack is unavailable.
"""

from __future__ import annotations

import importlib.util
import unittest


FULL_WEB_STACK = all(
    importlib.util.find_spec(name) is not None
    for name in ("gradio", "openai", "chromadb", "sentence_transformers")
)


@unittest.skipUnless(FULL_WEB_STACK, "Web dependency stack is not installed.")
class WebSmokeTests(unittest.TestCase):
    def test_ui_contains_core_components(self) -> None:
        from src.config import get_settings
        from src.web_gradio import build_demo

        demo = build_demo(get_settings())
        component_types = {type(item).__name__ for item in demo.blocks.values()}

        self.assertIn("File", component_types)
        self.assertIn("Chatbot", component_types)
        self.assertIn("Textbox", component_types)
        self.assertIn("Button", component_types)


if __name__ == "__main__":
    unittest.main()
