# Answer from the source code

Answer the question below using ONLY the repository you can reach through the
tools. You have not seen any documentation about this and you should not
assume what it says.

## Question

{{question}}

## Scope

Component or area: {{heading_path}}
Product version: {{declared_version}}

## Tools

- `search_code(query, limit)` — search the repository
- `read_file(path, line_start, line_end)` — read a file or range
- `list_symbols(path)` — symbols defined in a file

Every result comes back with an `evidence_id`. When you cite, cite by
`evidence_id`. You cannot cite anything you have not opened, and you must not
write file paths or line numbers yourself.

Budget: {{max_tool_calls}} tool calls.

## How to work

1. Search for the concept, then read the actual definition. A search snippet
   is a pointer, not an answer.
2. Prefer the definition site over a usage site. A caller passing 30 does not
   establish that 30 is the default.
3. Check whether a value is overridden elsewhere before reporting it.
4. Cite the narrowest range that contains the answer. A hundred-line citation
   is not evidence for a one-line fact.

## Saying you could not find it

If the code does not settle the question, say so. Return an empty answer and
no citations.

This is a correct and useful outcome. A guess is not, because a guess is
indistinguishable from a finding once it reaches the dashboard, and somebody
will edit their documentation because of it.

Do not answer from general knowledge of how such systems usually work. The
only thing that counts is what is in this repository.

## Output

{{output_schema}}

`justification` explains what the cited lines show, in one or two sentences,
for a reader who will open them.
