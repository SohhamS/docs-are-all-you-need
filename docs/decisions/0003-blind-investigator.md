# 0003. The investigator is blind, and evidence is checked twice

Status: accepted

## Context

Two questions, closely related, about how the code-side answer is produced and
trusted.

## Decision

**The investigator never receives `doc_answer` or `raw_text`.**

**Both evidence checks run on every claim**: deterministic authenticity, then
semantic sufficiency. A failed authenticity check is terminal and no model is
consulted about it.

## Why blind

Comparing the investigator's answer to the document's answer only means
something if the two were reached independently. Show a model what the
document claims and it drifts toward confirming it. The correct bucket
inflates, and the pipeline becomes an expensive way to agree with whatever was
already written.

The cost is real: the investigator has less context, so questions must be
self-contained. That obligation lands on the classify stage, where it belongs,
because that is the stage that can see the document.

## Why both checks

The tempting design is: run the deterministic check, and only if it fails, ask
a model. That looks like a pure cost saving. It is the system's worst failure
mode.

Authenticity passing tells you the model did not invent a file path. It tells
you **nothing about relevance**. An investigator can cite a real file, at real
line numbers, with nothing to do with the question, pass the deterministic
check, and reach the judge with a confidently wrong answer wearing a
"verified" badge. The judge compares that wrong answer to a correct document
and marks correct documentation as incorrect. A human applies the patch and a
good document is damaged, quietly.

Authenticity and sufficiency are orthogonal properties. Checking one does not
substitute for the other.

## Why a failed authenticity check is terminal

If the file does not exist, or the lines are out of bounds, or the snippet
hash does not match, the citation is fabricated or stale. No reasoning makes a
fabricated citation real; sending it to a model spends a call to reach a
conclusion already in hand.

The one genuinely recoverable case, a real citation written in a slightly
wrong format, is prevented upstream instead: the tool contract only lets the
model cite refs it was handed. Fix the contract, delete the node.

## Consequences

- Question self-containment is a hard requirement on classify, and should be
  tested by answering questions with no document context and seeing whether
  they are even interpretable.
- `codetools/protocol.py` must return line-accurate citations, which makes it
  the project's one blocking external dependency. See `mcp-tool-spec.md`.
- Every claim costs a sufficiency call. Accepted deliberately.
