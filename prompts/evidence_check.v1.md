# Does this evidence support this answer?

You are checking one thing only: whether the cited code actually establishes
the answer given. You are not checking whether the answer is true in general,
and you have no information about any documentation.

The citations have already been verified to exist exactly as cited. Your job
is relevance and sufficiency, not authenticity.

## Answer given

{{response_answer}}

## Question it answers

{{question}}

## Cited code

{{evidence_blocks}}

## Decide

`supported: true` only if the cited lines, read on their own, establish the
answer.

`supported: false` if:

- the citations are about something adjacent but not this question
- they show a value somewhere but not that it is the value asked about
  (a caller passing 30 is not a default of 30)
- they would need an assumption not visible in the cited lines
- they are so broad that they do not pin anything down

Being cautious here is cheap. A claim marked unsupported costs one human
glance. A claim wrongly marked supported can end up telling someone to edit
correct documentation.

## Output

{{output_schema}}
