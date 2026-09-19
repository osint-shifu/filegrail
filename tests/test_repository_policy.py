"""Repository controls that protect releases independently of operator discipline."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
WORKFLOWS = (
    ROOT / ".github" / "workflows" / "ci.yml",
    ROOT / ".github" / "workflows" / "release.yml",
)


def _workflow(name: str) -> str:
    return (ROOT / ".github" / "workflows" / name).read_text()


def test_release_verifies_the_tagged_master_commit_before_publishing():
    workflow = _workflow("release.yml")

    verify = workflow.index("  verify:")
    publish = workflow.index("  publish:")

    assert verify < publish
    assert "git fetch --depth=1 origin master:refs/remotes/origin/master" in workflow
    assert 'test "$(git rev-parse HEAD)" = "$(git rev-parse origin/master)"' in workflow
    assert 'test "v$VERSION" = "$GITHUB_REF_NAME"' in workflow
    assert 'python-version: ["3.10", "3.13"]' in workflow
    assert "ruff check ." in workflow
    assert "ruff format --check ." in workflow
    assert "pytest" in workflow
    assert "mypy" in workflow
    assert "python -m build" in workflow
    assert "twine check dist/*" in workflow
    assert re.search(r"(?ms)^  publish:\n.*?^    needs: verify$", workflow)


def test_github_actions_are_pinned_to_commit_shas():
    uses = []
    for path in WORKFLOWS:
        uses.extend(re.findall(r"(?m)^\s*- uses: [^@\s]+@([^\s#]+)", path.read_text()))

    assert uses
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in uses), uses


def test_local_agent_output_is_not_a_commit_candidate():
    ignored = (ROOT / ".gitignore").read_text().splitlines()

    assert "Claude outputs/" in ignored
