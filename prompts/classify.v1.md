# Classify units

You are given numbered units from one technical document. For EACH unit,
decide what kind of assertion it makes, and where it makes a factual claim
that reading source code could settle, write the question it answers and the
answer the document gives.

## Document context

Title: {{doc_title}}
Section: {{heading_path}}
Product version described: {{declared_version}}

## Units

{{units}}

## Claim types

- `code_verifiable` — a factual assertion that reading the source settles.
  Defaults, limits, names, signatures, return values, supported options,
  ordering, error conditions.
- `behavioural` — about runtime behaviour that would need running the system,
  not just reading it.
- `conceptual` — intent, rationale, guidance, roadmap. No code can make it
  true or false.
- `navigational` — headings, cross-references, boilerplate.
- `none` — no assertion at all.

## Writing the question

**The person answering your question will never see this document.** They have
the source code and nothing else.

So the question must carry its own context. Names, types, components, the
version. Resolve every pronoun and every "this".

    bad:  "What is the default timeout?"
    good: "What is the default value of the `request_timeout` option on the
           Go client's `Config` struct?"

A question that only makes sense next to this paragraph will get a confident
wrong answer, which is worse than no answer.

## Atomicity

One unit may hold several independent facts. Emit one entry per fact, all
carrying the same `unit_id`.

    "The client retries 3 times with exponential backoff, capped at 30s."
      -> how many times does the client retry?
      -> what backoff strategy does the client use?
      -> what is the cap on the client's backoff interval?

## Rules

- Return an entry for EVERY unit id you were given. Omitting one is an error.
- Never invent a unit id.
- `doc_answer` must be what the document says, not what you believe is true.
- For any type other than `code_verifiable`, leave `question` and `doc_answer`
  empty.

## Output

{{output_schema}}
