import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest


MODULE_PATH = pathlib.Path(__file__).with_name("validate_candidate.py")
SPEC = importlib.util.spec_from_file_location("validate_candidate", MODULE_PATH)
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


class CandidateValidatorTests(unittest.TestCase):
    def repository(self, directory):
        repository = pathlib.Path(directory)
        subprocess.run(["git", "init"], cwd=repository, check=True, capture_output=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.com",
                "commit",
                "--allow-empty",
                "-m",
                "base",
            ],
            cwd=repository,
            check=True,
            capture_output=True,
        )
        return repository

    def candidate(self, repository, base_commit, path="go.mod"):
        candidate = {
            "schemaVersion": "1",
            "repository": {
                "name": "azure-container-networking",
                "targetBranch": "sre-agent-gh-aw-eval",
                "baseCommit": base_commit,
            },
            "module": ".",
            "branch": "dependabot-security/root-security",
            "title": "Security update",
            "description": "Update dependency",
            "dependencies": [],
            "vulnerabilities": [],
            "changesets": [
                {
                    "reason": "update dependencies",
                    "files": [
                        {
                            "path": path,
                            "mode": "updated",
                            "contentEncoding": "utf-8",
                            "content": "module example.com/test\n",
                        }
                    ],
                }
            ],
        }
        candidate_path = repository / "candidate.json"
        candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
        return candidate_path

    def test_accepts_exact_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = self.repository(directory)
            base_commit = TOOL._git_head(repository)
            candidate, files, summary = TOOL.validate(
                self.candidate(repository, base_commit),
                repository,
                "azure-container-networking",
                "sre-agent-gh-aw-eval",
                base_commit,
            )
        self.assertEqual(".", candidate["module"])
        self.assertEqual(["go.mod"], summary["changedPaths"])
        self.assertEqual(1, len(files))

    def test_rejects_non_dependency_path(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = self.repository(directory)
            base_commit = TOOL._git_head(repository)
            with self.assertRaisesRegex(ValueError, "not allowed"):
                TOOL.validate(
                    self.candidate(repository, base_commit, "source.go"),
                    repository,
                    "azure-container-networking",
                    "sre-agent-gh-aw-eval",
                    base_commit,
                )

    def test_rejects_stale_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = self.repository(directory)
            base_commit = TOOL._git_head(repository)
            with self.assertRaisesRegex(ValueError, "stale"):
                TOOL.validate(
                    self.candidate(repository, "a" * 40),
                    repository,
                    "azure-container-networking",
                    "sre-agent-gh-aw-eval",
                    base_commit,
                )


if __name__ == "__main__":
    unittest.main()
