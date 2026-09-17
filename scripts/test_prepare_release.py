import unittest

from prepare_release import replace_package_version, validate_version_input


class PrepareReleaseTests(unittest.TestCase):
    def test_accepts_cargo_prerelease_version(self):
        validate_version_input("0.1.0-rc.1")

    def test_accepts_valid_bump_version(self):
        validate_version_input("0.1.0")

    def test_rejects_bootstrap_baseline(self):
        with self.assertRaisesRegex(ValueError, "bootstrap baseline 0.0.0"):
            validate_version_input("0.0.0")

    def test_rejects_invalid_semver(self):
        with self.assertRaisesRegex(ValueError, "invalid semver"):
            validate_version_input("v0.1")

    def test_rejects_subject_over_commit_limit(self):
        with self.assertRaisesRegex(ValueError, "exceed 72 characters"):
            validate_version_input(f"0.1.0-{'a' * 60}")

    def test_replaces_root_package_version(self):
        manifest = '[package]\nname = "somelse"\nversion = "0.0.0"\n\n[features]\n'
        self.assertEqual(
            replace_package_version(manifest, "0.0.0", "0.1.0-rc.1"),
            '[package]\nname = "somelse"\nversion = "0.1.0-rc.1"\n\n[features]\n',
        )

    def test_replace_package_version_rejects_mismatch(self):
        manifest = '[package]\nname = "somelse"\nversion = "0.0.0"\n'
        with self.assertRaises(ValueError):
            replace_package_version(manifest, "0.1.0", "0.2.0")

    def test_replace_package_version_requires_version_field(self):
        manifest = '[package]\nname = "somelse"\n'
        with self.assertRaises(ValueError):
            replace_package_version(manifest, "0.0.0", "0.1.0")

    def test_replace_package_version_rejects_multiple_matches(self):
        manifest = (
            '[package]\nname = "somelse"\nversion = "0.0.0"\n'
            'name = "somelse"\nversion = "0.0.0"\n'
        )
        with self.assertRaises(ValueError):
            replace_package_version(manifest, "0.0.0", "0.1.0")

    def test_requires_package_version(self):
        with self.assertRaisesRegex(ValueError, "expected one package version"):
            replace_package_version('[package]\nname = "somelse"\n', "0.0.0", "0.1.0")


if __name__ == "__main__":
    unittest.main()
