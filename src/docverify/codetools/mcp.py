"""`CodeTools` backed by a code MCP server (gitnexus or equivalent).

IMPLEMENTATION NOTES
--------------------
Before writing this, read `docs/mcp-tool-spec.md`. It specifies the response
shape this adapter needs. If the server cannot produce it, the spec is the
document to negotiate from.

The adapter's job is narrow: call the server, then map whatever it returns
into `CodeRef`. If a returned result lacks a path or a line range, this
adapter must NOT invent one. Drop the result and log it. A guessed line
number defeats the authenticity check, which is the only thing standing
between a hallucinated citation and a "your documentation is wrong" verdict.

`snippet_sha256` must be computed over exactly the text the server returned
for the cited lines, so that `verify_ref` can detect drift.
"""

from __future__ import annotations

from docverify.models import CodeRef


class McpCodeTools:
    """See `docverify.codetools.protocol.CodeTools`."""

    def __init__(self, url: str, token: str | None, repo: str, timeout_s: float = 60.0) -> None:
        self.url = url
        self.token = token
        self._repo = repo
        self.timeout_s = timeout_s
        self._ref: str = ""

    @property
    def repo(self) -> str:
        return self._repo

    @property
    def ref(self) -> str:
        if not self._ref:
            raise RuntimeError("resolve_ref() must be called once at run start")
        return self._ref

    async def resolve_ref(self, branch: str) -> str:
        raise NotImplementedError

    async def search_code(self, query: str, *, limit: int = 20) -> list[CodeRef]:
        raise NotImplementedError

    async def read_file(
        self, path: str, *, line_start: int = 1, line_end: int | None = None
    ) -> CodeRef:
        raise NotImplementedError

    async def list_symbols(self, path: str) -> list[CodeRef]:
        raise NotImplementedError

    async def verify_ref(self, ref: CodeRef) -> bool:
        raise NotImplementedError
