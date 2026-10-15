import argparse
import fnmatch
import json
import pathlib
import re
import subprocess
import sys


ALLOWED_PATHS = ("go.mod", "go.sum", "*/go.mod", "*/go.sum")
SCHEMA_VERSION = "1"


def _git_head(repository):
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _under(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def validate(candidate_path, repository, repository_name, target_branch, base_commit):
    candidate_path = candidate_path.resolve()
    repository = repository.resolve()
    if not _under(candidate_path, repository):
        raise ValueError("candidate path must be inside the checked-out repository")

    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if candidate.get("schemaVersion") != SCHEMA_VERSION:
        raise ValueError("unsupported candidate schemaVersion")

    candidate_repository = candidate.get("repository") or {}
    if candidate_repository.get("name") != repository_name:
        raise ValueError("candidate repository does not match")
    if candidate_repository.get("targetBranch") != target_branch:
        raise ValueError("candidate target branch does not match")
    if candidate_repository.get("baseCommit") != base_commit:
        raise ValueError("candidate base commit is stale")
    if _git_head(repository) != base_commit:
        raise ValueError("checked-out repository is not at the requested base commit")

    branch = candidate.get("branch", "")
    branch = re.sub(r"[^A-Za-z0-9._/-]+", "-", branch).strip("/-")
    if not branch:
        raise ValueError("candidate branch is empty")
    branch = f"sre-agent-gh-aw/cve-{branch}"[:200]

    files = [
        file_change
        for changeset in candidate.get("changesets", [])
        for file_change in changeset.get("files", [])
    ]
    if not files:
        raise ValueError("candidate contains no file changes")

    seen = set()
    for file_change in files:
        path = file_change.get("path", "").lstrip("/")
        if not path or path in seen:
            raise ValueError("candidate contains an empty or duplicate path")
        seen.add(path)
        if not any(fnmatch.fnmatch(path, pattern) for pattern in ALLOWED_PATHS):
            raise ValueError(f"candidate path is not allowed: {path}")
        if file_change.get("contentEncoding") != "utf-8":
            raise ValueError(f"unsupported content encoding for {path}")
        destination = (repository / path).resolve()
        if not _under(destination, repository):
            raise ValueError(f"candidate path escapes repository: {path}")

    return candidate, files, {
        "schemaVersion": SCHEMA_VERSION,
        "module": candidate.get("module"),
        "branch": branch,
        "title": candidate.get("title"),
        "description": candidate.get("description"),
        "changedPaths": sorted(seen),
        "dependencies": candidate.get("dependencies", []),
        "vulnerabilities": candidate.get("vulnerabilities", []),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--repository", default="azure-container-networking")
    parser.add_argument("--target-branch", required=True)
    parser.add_argument("--base-commit", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    repository = pathlib.Path.cwd().resolve()
    candidate, files, summary = validate(
        pathlib.Path(args.candidate),
        repository,
        args.repository,
        args.target_branch,
        args.base_commit,
    )
    if args.apply:
        for file_change in files:
            path = file_change["path"].lstrip("/")
            destination = repository / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(file_change["content"], encoding="utf-8")
        summary["applied"] = True
    else:
        summary["applied"] = False

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"candidate validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
