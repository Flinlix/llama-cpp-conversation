# 0031. The caches of conversations a begin switched away from are kept, within a RAM bound that defaults to none

Date: 2026-11-19

## Context

A server that serves several conversations on one model switches between them
with `begin`, and each switch decoded the other conversation again from the
start. The owner asked for a RAM bound, and that a bound of 0 switch the
feature off.

## Decision

- `kept_conversation_bytes` bounds the host RAM the caches of conversations a
  begin switched away from may take. The default, 0, keeps none and switches
  the feature off.
- Where a begin leaves more than 256 tokens of the cache behind, the whole
  cache is saved (`save_whole_state`, in the protocol) with its tokens. Where a
  kept one shares more than 256 tokens more of the new conversation than the
  cache does, it is restored instead and what differs from it is decoded. The
  entry is taken out of the store before anything else is kept.
- The oldest kept goes first; one that alone exceeds the bound is not kept,
  and its size is asked of the engine before it is saved, so that it is never
  copied out. The bound holds once they are kept; while one is saved it takes
  its own size beside them. Where a context of one's own saves a state larger
  than the bound, a whole state is not saved again for a cache at least as
  long as that one.
- Only a begin keeps or switches; an eviction never does.
- A cache that can neither shift nor cut keeps no conversation.
- A failed action puts the kept conversations back as they were.
- The whole cache is saved for every sequence, so that it keeps the positions
  its window layers no longer attend over (0060, 2026-11-21).
- A shift waits in llama.cpp for the next decode; a state saved before it
  holds the keys unshifted, so the newest token is decoded again first where a
  shift waits (found by review on 2026-11-21: the switch back then answered
  from wrongly placed keys, the most likely next token changed). Where that
  token is not known, the conversation is not kept.

## Consequences

- Switching back to a kept conversation decodes only what differs from it.
- A kept conversation takes the model's cache per token times its tokens.
  Measured on 2026-11-21: 874.5 MiB for 4,070 tokens with Gemma 4 26B A4B on
  an RTX 3090, about 220 KiB per token, copied from the card in 0.4 s; 36 MiB
  for 2,047 tokens with Gemma 4 E2B on the processor, about 18 KiB per token.
  Before the size was asked first, a state larger than the bound was copied
  out in full and thrown away, once per conversation length; asking the size
  takes 0.1 to 0.3 ms.
- The RAM is spent only where the caller sets a bound.

## Alternatives rejected

- Keeping conversations on a cache that can neither shift nor cut: going back
  restored the whole cache but not the partial states it returns to, so the
  next change near its end decoded everything again (2,299 tokens against 36
  in one measured run). Keeping those states with each conversation is left
  until such a model needs it.
