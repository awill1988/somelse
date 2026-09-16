import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from release_gate import (
    compare_versions,
    previous_version,
    published_versions,
    release_decision,
    sparse_index_path,
    tag_target,
)


class ReleaseGateTests(unittest.TestCase):
    def test_semver_prerelease_precedence(self):
        self.assertLess(compare_versions("0.2.0-beta.2", "0.2.0-beta.11"), 0)
        self.assertLess(compare_versions("0.2.0-beta.11", "0.2.0"), 0)
        self.assertGreater(compare_versions("0.2.0", "0.1.9"), 0)

    def test_build_metadata_does_not_increase_precedence(self):
        self.assertEqual(compare_versions("0.2.0+build.2", "0.2.0+build.1"), 0)

    def test_sparse_index_path(self):
        self.assertEqual(sparse_index_path("rust_crate"), "ru/st/rust_crate")
        self.assertEqual(sparse_index_path("a"), "1/a")
        self.assertEqual(sparse_index_path("ab"), "2/ab")
        self.assertEqual(sparse_index_path("abc"), "3/a/abc")

    def test_unchanged_bootstrap_baseline_skips_release(self):
        self.assertEqual(
            release_decision("0.0.0", "0.0.0", "0.0.0", []),
            (False, False),
        )

    def test_bootstrap_baseline_never_published(self):
        # Even if previous was 0.0.0, current 0.0.0 must yield (False, False)
        self.assertEqual(
            release_decision("0.0.0", "0.0.0", "0.0.0", []),
            (False, False),
        )

    def test_first_version_bump_from_bootstrap_releases(self):
        self.assertEqual(
            release_decision("0.1.0", "0.0.0", "0.0.0", []),
            (True, True),
        )

    def test_first_prerelease_bump_from_bootstrap_releases(self):
        self.assertEqual(
            release_decision("0.1.0-alpha.1", "0.0.0", "0.0.0", []),
            (True, True),
        )

    def test_prerelease_progression_releases(self):
        self.assertEqual(
            release_decision(
                "0.1.0-rc.2",
                "0.1.0-rc.1",
                "0.0.0",
                ["0.1.0-rc.1"],
            ),
            (True, True),
        )

    def test_stable_promotion_releases(self):
        self.assertEqual(
            release_decision(
                "0.1.0",
                "0.1.0-rc.2",
                "0.0.0",
                ["0.1.0-rc.1", "0.1.0-rc.2"],
            ),
            (True, True),
        )

    def test_decrease_fails(self):
        with self.assertRaises(ValueError):
            release_decision("0.1.0", "0.2.0", "0.0.0", [])

    def test_baseline_reset_after_publish_fails(self):
        with self.assertRaises(ValueError):
            release_decision("0.0.0", "0.1.0", "0.0.0", ["0.1.0"])

    def test_published_duplicate_fails_even_if_yanked(self):
        with self.assertRaises(ValueError):
            release_decision("0.2.0", "0.1.0", "0.0.0", ["0.1.0", "0.2.0"])

    def test_matching_recovery_tag_skips_publish(self):
        self.assertEqual(
            release_decision(
                "0.2.0",
                "0.1.0",
                "0.0.0",
                ["0.1.0", "0.2.0"],
                recovery_tag_matches=True,
            ),
            (True, False),
        )

    def test_recovery_rejects_newer_registry_version(self):
        with self.assertRaises(ValueError):
            release_decision(
                "0.2.0",
                "0.1.0",
                "0.0.0",
                ["0.1.0", "0.2.0", "0.3.0"],
                recovery_tag_matches=True,
            )

    def test_registry_version_ahead_fails(self):
        with self.assertRaises(ValueError):
            release_decision("0.2.0", "0.1.0", "0.0.0", ["0.1.0", "0.3.0-beta.1"])

    def test_unpublished_prior_bump_fails(self):
        with self.assertRaises(ValueError):
            release_decision("0.3.0", "0.2.0", "0.0.0", ["0.1.0"])

    def test_missing_crate_has_no_published_versions(self):
        with patch(
            "release_gate.urlopen",
            side_effect=HTTPError("https://index.crates.io/ru/st/rust_crate", 404, "", {}, None),
        ):
            self.assertEqual(published_versions("rust_crate"), [])

    def test_registry_error_fails_closed(self):
        with patch("release_gate.urlopen", side_effect=URLError("unavailable")):
            with self.assertRaises(RuntimeError):
                published_versions("rust_crate")

    def test_zero_sha_resolves_to_bootstrap_baseline(self):
        self.assertEqual(previous_version("0000000000000000000000000000000000000000"), "0.0.0")
        self.assertEqual(previous_version(""), "0.0.0")

    @patch("release_gate.subprocess.run")
    def test_tag_target_resolves_commit(self, run):
        run.return_value.returncode = 0
        run.return_value.stdout = "abc123\n"
        self.assertEqual(tag_target("0.1.0-rc.1"), "abc123")

    @patch("release_gate.subprocess.run")
    def test_missing_tag_has_no_target(self, run):
        run.return_value.returncode = 128
        run.return_value.stdout = ""
        self.assertIsNone(tag_target("0.1.0-rc.1"))


if __name__ == "__main__":
    unittest.main()
