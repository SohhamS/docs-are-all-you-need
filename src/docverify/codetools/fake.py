"""An in-memory `CodeTools` backed by a dict of files.

Fully implemented on purpose. It lets the entire pipeline run, be tested and
be demonstrated before the real code MCP server exists, which decouples this
work from a dependency the team does not yet control.

It also gives the authenticity check something to fail against: `verify_ref`
here does real snippet hashing, so a test can hand the evidence stage a
fabricated citation and assert the claim comes out UNVERIFIABLE.
"""

from __future__ import annotations

import hashlib

from docverify.models import CodeRef


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class FakeCodeTools:
    """See `docverify.codetools.protocol.CodeTools`."""

    def __init__(
        self,
        files: dict[str, str],
        *,
        repo: str = "fake/repo",
        ref: str = "0" * 40,
    ) -> None:
        self._files = files
        self._repo = repo
        self._ref = ref

    @property
    def repo(self) -> str:
        return self._repo

    @property
    def ref(self) -> str:
        return self._ref

    async def resolve_ref(self, branch: str) -> str:
        return self._ref

    def _lines(self, path: str) -> list[str]:
        if path not in self._files:
            raise FileNotFoundError(path)
        return self._files[path].splitlines()

    def _make_ref(self, path: str, line_start: int, line_end: int) -> CodeRef:
        lines = self._lines(path)
        line_start = max(1, line_start)
        line_end = min(len(lines), line_end)
        snippet = "\n".join(lines[line_start - 1 : line_end])
        return CodeRef(
            repo=self._repo,
            ref=self._ref,
            path=path,
            line_start=line_start,
            line_end=line_end,
            snippet=snippet,
            snippet_sha256=_sha(snippet),
        )

    async def search_code(self, query: str, *, limit: int = 20) -> list[CodeRef]:
        needle = query.lower()
        results: list[CodeRef] = []
        for path, content in self._files.items():
            for i, line in enumerate(content.splitlines(), start=1):
                if needle in line.lower():
                    results.append(self._make_ref(path, i, i))
                    if len(results) >= limit:
                        return results
        return results

    async def read_file(
        self, path: str, *, line_start: int = 1, line_end: int | None = None
    ) -> CodeRef:
        lines = self._lines(path)
        return self._make_ref(path, line_start, line_end or len(lines))

    async def list_symbols(self, path: str) -> list[CodeRef]:
        # Deliberately naive. A fake that pretends to do real symbol analysis
        # would let tests pass for the wrong reasons.
        refs: list[CodeRef] = []
        for i, line in enumerate(self._lines(path), start=1):
            stripped = line.strip()
            if stripped.startswith(("def ", "class ", "func ", "public ", "private ")):
                refs.append(self._make_ref(path, i, i))
        return refs

    async def verify_ref(self, ref: CodeRef) -> bool:
        if ref.repo != self._repo or ref.ref != self._ref:
            return False
        if ref.path not in self._files:
            return False
        lines = self._lines(ref.path)
        if ref.line_start < 1 or ref.line_end > len(lines) or ref.line_start > ref.line_end:
            return False
        actual = "\n".join(lines[ref.line_start - 1 : ref.line_end])
        return _sha(actual) == ref.snippet_sha256
