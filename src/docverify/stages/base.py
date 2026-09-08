"""The stage contract.

A stage is a function from typed input to typed output. It does not know that
a database exists, that a queue exists, or where its input came from. That is
enforced by convention rather than by the type system, so it is stated here
and repeated in AGENTS.md:

    NOTHING IN `docverify/stages/` MAY IMPORT `store`, `bus` OR `orchestrator`.

What a stage gets is a `StageContext`: the collaborators it needs, already
built and configured. What it returns is a value. The orchestrator persists
that value, decides what happens next, and handles retries.

The payoff is that every stage is testable with fakes and no infrastructure,
and that swapping the transport or the database later touches three files.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from docverify.codetools.protocol import CodeTools
from docverify.config import Config
from docverify.llm.router import LLMRouter

InT = TypeVar("InT")
OutT = TypeVar("OutT")


@dataclass(frozen=True)
class StageContext:
    """Everything a stage is allowed to reach.

    Note what is absent: no store, no bus. If a stage needs data it was not
    given, the fix is to pass it in, not to reach for the database.
    """

    config: Config
    llm: LLMRouter
    codetools: CodeTools
    run_id: str
    doc_id: str = ""
    claim_id: str = ""

    def trace(self, stage: str) -> dict[str, str]:
        """Trace attributes for this unit of work."""
        return {
            "run_id": self.run_id,
            "doc_id": self.doc_id,
            "claim_id": self.claim_id,
            "stage": stage,
        }


class StageError(Exception):
    """A stage failed in a way that should be retried or marked FAILED.

    Deliberately distinct from producing an UNVERIFIABLE verdict. A stage
    error means the machinery broke; UNVERIFIABLE means the machinery worked
    and the answer was genuinely not determinable. They belong in different
    queues and in front of different people.
    """


class Stage(Protocol[InT, OutT]):
    name: str

    async def run(self, ctx: StageContext, payload: InT) -> OutT: ...


def load_prompt(config: Config, name: str, version: str) -> str:
    """Read a versioned prompt from `prompts/`.

    Prompts are files, not string literals, and they carry a version in the
    filename. Every stored result records which version produced it, so a
    verdict from last week stays explicable after the prompt changes.
    """
    from pathlib import Path

    path = Path(config.prompts_dir) / f"{name}.{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def render(template: str, **values: Any) -> str:
    """Substitute `{{name}}` placeholders in a prompt template.

    Deliberately not Jinja. A prompt with control flow in it is a prompt
    nobody can read as a whole, and the versioned-file scheme stops working
    when one file can render ten different ways.
    """
    out = template
    for key, value in values.items():
        out = out.replace("{{" + key + "}}", str(value))
    return out
