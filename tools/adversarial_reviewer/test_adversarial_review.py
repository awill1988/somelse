import unittest
from pathlib import Path

from adversarial_review import (
    format_review_report,
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
        report = run_mock_reviewer(diff, ["src/lib.rs"])
        self.assertIn("VERDICT: PASS", report)
        self.assertIn("No Soundness Violations", report)

    def test_mock_reviewer_flags_std_leak(self):
        diff = "+ use std::collections::HashMap;"
        report = run_mock_reviewer(diff, ["src/lib.rs"])
        self.assertIn("VERDICT: CRITICAL", report)
        self.assertIn("std` leakage", report)

    def test_mock_reviewer_flags_ai_attribution(self):
        diff = "+ Co-authored-by: robot <robot@example.com>"
        report = run_mock_reviewer(diff, ["src/lib.rs"])
        self.assertIn("VERDICT: CRITICAL", report)
        self.assertIn("AI attribution", report)

    def test_format_review_report_parses_verdicts(self):
        report_pass, verdict_pass = format_review_report("analysis details\nVERDICT: PASS", ["src/lib.rs"])
        self.assertEqual(verdict_pass, "PASS")
        self.assertIn("`PASS`", report_pass)

        report_crit, verdict_crit = format_review_report("analysis details\nVERDICT: CRITICAL", ["src/lib.rs"])
        self.assertEqual(verdict_crit, "CRITICAL")
        self.assertIn("`CRITICAL`", report_crit)

        report_flag, verdict_flag = format_review_report("analysis details\nVERDICT: FLAGGED", ["src/lib.rs"])
        self.assertEqual(verdict_flag, "FLAGGED")
        self.assertIn("`FLAGGED`", report_flag)

    def test_load_model_env_parses_attributes(self):
        config = load_env(SCRIPT_DIR / "model.env")
        self.assertIn("MODEL_NAME", config)
        self.assertIn("MODEL_SHA256", config)
        self.assertIn("PRIMARY_MODEL_URL", config)
        self.assertEqual(config["MODEL_NAME"], "qwen2.5-coder-0.5b-instruct-q4_k_m.gguf")


if __name__ == "__main__":
    unittest.main()
