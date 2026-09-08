"""The code access seam.

THE MOST IMPORTANT CONTRACT IN THIS REPOSITORY.

Every method returns results that already carry `repo`, `ref`, `path`,
`line_start`, `line_end`, `snippet` and `snippet_sha256`. The investigator
cites by selecting among what it was handed. It never types a path or a line
number.

This is not a style preference. The deterministic authenticity check in the
`evidence` stage is only possible because citations are structurally
verifiable, and the check is what stops a model's fabricated file path from
becoming a confident "your documentation is wrong" on somebody's dashboard.

If the code MCP server cannot return line-accurate results, that is a
blocking problem for the design, not an inconvenience to work around by
letting the model write paths. See `docs/mcp-tool-spec.md` for the response
specification to hand to whoever builds that server.
"""

from __future__ import annotations

from typing import Protocol

from docverify.models import CodeRef


class CodeTools(Protocol):
    """Read-only access to the source repository at a pinned commit.

    Phase 1 is read-only. Nothing here executes code, and nothing may be added
    that does; sandboxed execution of samples found in documents is a phase 2
    item with its own security review.
    """

    @property
    def repo(self) -> str: ...

    @property
    def ref(self) -> str:
        """The pinned commit SHA. Constant for the lifetime of a run."""
        ...

    async def resolve_ref(self, branch: str) -> str:
        """Resolve a branch name to a commit SHA.

        Called ONCE at run start. Every subsequent call in the run uses the
        returned SHA. A run that follows a moving branch produces results that
        cannot be reproduced or defended.
        """
        ...

    async def search_code(self, query: str, *, limit: int = 20) -> list[CodeRef]:
        """Search the repository. Results are line-accurate citations."""
        ...

    async def read_file(
        self, path: str, *, line_start: int = 1, line_end: int | None = None
    ) -> CodeRef:
        """Read a file or a range of it, as a citation."""
        ...

    async def list_symbols(self, path: str) -> list[CodeRef]:
        """Symbols defined in a file, each with its definition span.

        The product spans several languages (Go, Java, Python, C++, C#), so
        implementations should degrade gracefully: returning an empty list for
        an unsupported language is correct, guessing is not.
        """
        ...

    async def verify_ref(self, ref: CodeRef) -> bool:
        """Does this citation resolve exactly, at this commit?

        Used by the deterministic authenticity check. Must compare the stored
        `snippet_sha256` against the current content of the cited lines, not
        merely check that the file exists.
        """
        ...
