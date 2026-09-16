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
        manifest = '[package]\nname = "rust-crate-template"\nversion = "0.0.0"\n\n[features]\n'
        self.assertEqual(
            replace_package_version(manifest, "0.0.0", "0.1.0-rc.1"),
            '[package]\nname = "rust-crate-template"\nversion = "0.1.0-rc.1"\n\n[features]\n',
        )

    def test_preserves_dependency_versions(self):
        manifest = (
            '[package]\nversion = "0.0.0"\n\n'
            '[dependencies]\nexample = { version = "1.0.0" }\n'
        )
        self.assertIn(
            'example = { version = "1.0.0" }',
            replace_package_version(manifest, "0.0.0", "0.1.0"),
        )

    def test_rejects_metadata_mismatch(self):
        with self.assertRaisesRegex(ValueError, "does not match cargo metadata"):
            replace_package_version(
                '[package]\nversion = "0.0.1"\n',
                "0.0.0",
                "0.1.0",
            )

    def test_requires_package_version(self):
        with self.assertRaisesRegex(ValueError, "expected one package version"):
            replace_package_version('[package]\nname = "rust-crate-template"\n', "0.0.0", "0.1.0")


if __name__ == "__main__":
    unittest.main()
