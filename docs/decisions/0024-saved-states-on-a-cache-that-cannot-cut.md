# 0024. A cache that can neither shift nor cut goes back to a few saved states, kept where actions return

Date: 2026-11-19

## Context

A cache that holds a running state cannot be cut at its end or shifted, so
the only way back to an earlier point, short of decoding again from the start,
is a state saved there. Each save copies the model's state in RAM, and a save
before the first word delays the answer.

## Decision

- Only a cache that can neither shift nor cut saves states; one that cuts or
  shifts saves none.
- States are kept, each only for as long as the tokens before it stay:
  - the newest states the cache rested in;
  - one where each of the two newest exchanges begins, the places taken only
    from renders the action made;
  - the states of the two newest cuts where the template moves its
    declarations to the newest question;
  - where a reply's turn begins, only where the template writes a past reply
    otherwise than the cache holds it after the reply (reasoning on, or a
    template whose past reply does not stand as its generation prompt left it,
    `writes_reply_as_prompted`);
  - where a generation starts and where a first question's run starts.
  None is pinned inside the system turn, and none within 32 tokens
  (`_NEAR_STATE_TOKENS`) of the start or of the state kept where the opening
  ends: going back there decodes those tokens instead. A state saved where
  another is asked for serves both. A cache that cannot cut saves one state per reply, where
  its question's text ends.
- A state is saved into a buffer that no kept state refers to, of its size,
  where one is there; at most one such spare is kept.

## Consequences

- Measured on the stand-in, Ministral 2410 with a tool: after keeping the state
  before moved declarations, 389 tokens per turn where every turn had decoded
  the whole conversation again (1,535 to 1,979).
- On Qwen 3.5 9B the state pinned before the oldest question cut the total
  decode by 9 and 39 percent (0023).
- A shortened reply decodes the newest question again from where its exchange
  begins, and the end of that turn and the generation prompt (about ten
  tokens).
- Measured: saving 64 MB into a new buffer took 31.5 ms, into a
  reused one 5.1 ms.
- Measured on 2026-11-21 on Qwen 3.5 9B (RTX 3090, context 8192): each state
  takes 50.25 MiB, and a 17-token system turn had one of its own before the
  bound of 32 tokens applied to it. The bound weighs one state's RAM against
  decoding at most 32 tokens again. Going back to the opening is followed by
  decoding the rest of the conversation, hundreds to thousands of tokens, so
  the 32 add about 1 to 3 percent to that decode; they take about 50 ms at the
  594 tokens per second record 0014 gives for an i9-9900K's processor alone
  (both estimated). It was not measured on a Raspberry Pi.

## Alternatives rejected

- Saving a state after the question, before the first word, so that only the
  reply is decoded again: 23 ms per question on Qwen 3.5 9B and about 65 ms on
  the 27B models (RTX 3090), to spare a decode that runs after the answer.
- Two states per reply: saved the whole cache twice before every first word
  for a saving of about ten tokens on a later shortening.
