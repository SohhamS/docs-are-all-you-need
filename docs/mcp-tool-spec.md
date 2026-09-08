# Code access tool specification

What the code MCP server must provide for this pipeline to work. Hand this to
whoever builds or configures that server (gitnexus or otherwise).

## Why this document exists before the server does

The deterministic authenticity check is what stops a hallucinated file path
from becoming a confident "your documentation is wrong" on somebody's
dashboard. That check is only possible if every citation is
**machine-verifiable**, which means every tool response must carry an exact
repository, commit, path and line range, plus the snippet text.

If the server cannot do this, the design changes and the change is not small.
That makes it the one blocking unknown in the project, and it is worth
settling before much implementation happens on top of it.

`FakeCodeTools` implements this specification exactly, so everything else can
be built and tested while the question is open.

---

## Required response shape

Every result from every tool must be mappable to:

```json
{
  "repo":          "org/product",
  "ref":           "a1b2c3d4e5f6...",
  "path":          "src/config/server.go",
  "line_start":    40,
  "line_end":      45,
  "snippet":       "func NewServer(...) *Server {\n    timeout := 30 * time.Second\n...",
  "snippet_sha256":"9f86d081884c7d65..."
}
```

| Field | Requirement |
|---|---|
| `repo` | Stable repository identifier. |
| `ref` | **Full commit SHA.** Never a branch name, never a tag. |
| `path` | Repository-root-relative. No leading `./`, no absolute paths. |
| `line_start`, `line_end` | 1-based, inclusive. `line_start <= line_end`. |
| `snippet` | Exactly the text of those lines at that commit, newline-joined, no added indentation or truncation marker. |
| `snippet_sha256` | Hex sha256 of `snippet` encoded UTF-8. May be computed client-side, but the snippet must be exact enough that recomputation is stable. |

A result that cannot supply a path and a line range is **dropped**, not
guessed at. The adapter in `codetools/mcp.py` must log and discard it. This is
the specific behaviour that a code-graph RAG makes tempting to get wrong:
graph nodes and relationships are not citations until they carry a location.

---

## Required operations

### `resolve_ref(branch) -> commit_sha`

Resolve a branch name to a full commit SHA. Called **once per run**. Every
subsequent call in that run passes the returned SHA, so that a merge midway
through a run cannot make its first and last claims disagree about the same
code.

### `search_code(query, limit) -> [CodeRef]`

Search the repository at the pinned commit. Semantic, lexical or hybrid, that
is the server's business. Each result must be line-accurate.

The product spans Go, Java, Python, C++ and C#, so this needs to work across
all of them.

### `read_file(path, line_start?, line_end?) -> CodeRef`

Read a file, or a range, at the pinned commit.

### `list_symbols(path) -> [CodeRef]`

Symbols defined in a file, each with its definition span. Multi-language, so
degrading is expected: **returning an empty list for an unsupported language
is correct; guessing is not.**

### `verify_ref(ref) -> bool`

Does this citation resolve exactly, right now, at this commit?

Must compare the stored `snippet_sha256` against the current content of the
cited lines. Checking only that the file exists is not sufficient and defeats
the purpose of the check.

If the server cannot offer this, the adapter can implement it with
`read_file` plus a local hash comparison. Confirm the fallback works before
relying on it.

---

## Constraints

- **Read only.** No write operation, no execution, no shell. Phase 1 reads
  code; sandboxed execution is a phase 2 item with its own security review.
- **Pinned.** Every call carries the run's commit SHA. A server that only
  serves HEAD makes runs unreproducible and is not sufficient.
- **Bounded.** `search_code` respects `limit`. A tool returning a thousand
  results will blow the investigator's context and its tool budget.
- **Honest about failure.** A missing path returns a clear error. It does not
  return the nearest match, because the investigator will cite the nearest
  match.

---

## Negotiating position, if the server cannot do this

In rough order of preference:

1. **Add line ranges to the existing responses.** Usually the smallest change,
   since the server already read the file to produce the result.
2. **Keep the graph search, add `read_file`.** The investigator can search the
   graph for candidates and then read the actual file to produce a citable
   ref. Costs an extra call per citation and is entirely acceptable.
3. **Wrap a plain repository checkout alongside the graph server.** The graph
   answers "where should I look", a simple file reader answers "what exactly
   is there". More moving parts, still correct.

What is **not** acceptable is letting the model write paths and line numbers
itself. That removes the only defence against a fabricated citation reaching a
human as a verified finding.
