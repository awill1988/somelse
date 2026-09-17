import json
import unittest
from pathlib import Path

from adversarial_review import (
    build_markdown_report,
    parse_model_output,
    run_mock_reviewer,
    should_ignore_file,
)
from fetch_model import load_env

SCRIPT_DIR = Path(__file__).parent.resolve()


class AdversarialReviewerTests(unittest.TestCase):
    def test_should_ignore_file(self):
        self.assertTrue(should_ignore_file("Cargo.lock"))
        self.assertTrue(should_ignore_file("README.md"))
        self.assertTrue(should_ignore_file("docs/index.md"))
        self.assertTrue(should_ignore_file("LICENSE-MIT"))
        self.assertTrue(should_ignore_file(".github/workflows/ci.yml"))
        self.assertTrue(should_ignore_file("tools/commit_check/src/main.rs"))

        self.assertFalse(should_ignore_file("src/lib.rs"))
        self.assertFalse(should_ignore_file("src/macro.rs"))
        self.assertFalse(should_ignore_file("tests/integration_tests.rs"))
        self.assertFalse(should_ignore_file("tests/fixtures/downstream/src/lib.rs"))

    def test_mock_reviewer_passes_clean_diff(self):
        diff = "+ let value = somelse!(opt, else => return Err(\"missing\"));"
        disp, findings, summary = run_mock_reviewer(diff, ["src/lib.rs"])
        self.assertEqual(disp, "APPROVE")
        self.assertEqual(len(findings), 0)
        self.assertIn("No soundness violations", summary)

    def test_mock_reviewer_flags_std_leak(self):
        diff = "+ use std::collections::HashMap;"
        disp, findings, summary = run_mock_reviewer(diff, ["src/lib.rs"])
        self.assertEqual(disp, "REQUEST_CHANGES")
        self.assertTrue(any(f["category"] == "no_std" for f in findings))
        self.assertIn("std leakage", findings[0]["title"])

    def test_mock_reviewer_flags_ai_attribution(self):
        diff = "+ Co-authored-by: robot <robot@example.com>"
        disp, findings, summary = run_mock_reviewer(diff, ["src/lib.rs"])
        self.assertEqual(disp, "REQUEST_CHANGES")
        self.assertTrue(any(f["category"] == "attribution" for f in findings))

    def test_parse_model_output_dispositions(self):
        disp, findings, _ = parse_model_output("Review complete.\nDISPOSITION: APPROVE")
        self.assertEqual(disp, "APPROVE")

        disp, findings, _ = parse_model_output("Found critical bug.\nDISPOSITION: REQUEST_CHANGES")
        self.assertEqual(disp, "REQUEST_CHANGES")

        disp, findings, _ = parse_model_output("Minor note on style.\nDISPOSITION: COMMENT")
        self.assertEqual(disp, "COMMENT")

    def test_build_markdown_report_formatting(self):
        findings = [{
            "severity": "critical",
            "category": "soundness",
            "file": "src/lib.rs",
            "line": 10,
            "title": "Unsafe macro expansion",
            "details": "Expression evaluated multiple times",
            "counterexample": "somelse!(expr, ...)",
        }]
        report = build_markdown_report("PR #1", "REQUEST_CHANGES", findings, "raw output", ["src/lib.rs"])
        self.assertIn("## 🔴 Adversarial Code Review: PR #1", report)
        self.assertIn("`REQUEST_CHANGES`", report)
        self.assertIn("[SOUNDNESS]", report)
        self.assertIn("somelse!(expr, ...)", report)

    def test_load_model_env_parses_attributes(self):
        config = load_env(SCRIPT_DIR / "model.env")
        self.assertIn("MODEL_NAME", config)
        self.assertIn("MODEL_SHA256", config)
        self.assertIn("PRIMARY_MODEL_URL", config)
        self.assertEqual(config["MODEL_NAME"], "qwen2.5-coder-0.5b-instruct-q4_k_m.gguf")


if __name__ == "__main__":
    unittest.main()
