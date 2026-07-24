import io
import pathlib
import tarfile
import tempfile
import unittest
from unittest import mock

from dss.connectors.acquire_github_snapshot import acquire


def archive_bytes() -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as bundle:
        for name, content in {
            "repo-commit/README.md": b"read me\n",
            "repo-commit/data/values.csv": b"id,value\nx,1\n",
            "repo-commit/private/raw.csv": b"not selected\n",
        }.items():
            member = tarfile.TarInfo(name)
            member.size = len(content)
            bundle.addfile(member, io.BytesIO(content))
    return output.getvalue()


class AcquireGithubSnapshotTest(unittest.TestCase):
    def test_selected_files_are_verified_without_extracting_other_members(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary)
            with mock.patch(
                "dss.connectors.acquire_github_snapshot._download",
                return_value=archive_bytes(),
            ):
                manifest = acquire(
                    "https://github.com/example/repo",
                    "a" * 40,
                    ["README.md", "data/*.csv"],
                    output,
                )
            self.assertEqual(manifest["integrity"], "verified")
            self.assertEqual(len(manifest["files"]), 2)
            self.assertTrue((output / "data" / "values.csv").is_file())
            self.assertFalse((output / "private" / "raw.csv").exists())
            self.assertEqual(
                {item["path"] for item in manifest["files"]},
                {"README.md", "data/values.csv"},
            )

    def test_unmatched_pattern_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch(
                "dss.connectors.acquire_github_snapshot._download",
                return_value=archive_bytes(),
            ):
                with self.assertRaisesRegex(RuntimeError, "matched no files"):
                    acquire(
                        "https://github.com/example/repo",
                        "b" * 40,
                        ["missing.csv"],
                        pathlib.Path(temporary),
                    )

    def test_rejects_non_pinned_or_unsafe_requests(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "full lowercase"):
                acquire(
                    "https://github.com/example/repo",
                    "main",
                    ["README.md"],
                    pathlib.Path(temporary),
                )
            with self.assertRaisesRegex(ValueError, "safe relative"):
                acquire(
                    "https://github.com/example/repo",
                    "c" * 40,
                    ["../README.md"],
                    pathlib.Path(temporary),
                )


if __name__ == "__main__":
    unittest.main()
