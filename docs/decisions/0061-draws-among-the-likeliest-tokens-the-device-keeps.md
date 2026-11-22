# 0061. Where layers run on a GPU, the draws are made among the likeliest tokens the device keeps

Date: 2026-11-22

## Context

Every generated token was drawn on the processor from the whole vocabulary:
the engine copied every token's logit from the device to host memory, and
the sampler chain sorted out the likeliest among them, while the device
waited for the next token. llama.cpp can run sampler stages on the device
(`llama_set_sampler`). A chain run wholly there draws the token itself, and
the logits never reach the host. The library's draws need them there: where
the turn may not end yet, a token that ends it is drawn again from the same
logits with the ending tokens withheld (0032), and a chain's withheld tokens
and penalties change from one generation to the next.

## Decision

- Where layers run on a GPU and the binding has `llama_set_sampler`, the
  context gives the device one stage, a top-k of `count` tokens, and keeps it
  between generations. Each decode then hands over only those tokens and
  their logits. The library's own sampler chains, unchanged, are applied to
  them in place of the whole vocabulary, a draw with tokens withheld
  included.
- `count` covers every token a draw can reach: the chain's own top-k (one
  token for greedy decoding), plus the penalty window where penalties apply
  (penalties lower at most that many tokens), plus the tokens a draw may
  withhold (call tags, a thought's opening, the turn's ending), at least 32
  of them (`_WITHHELD_ALLOWANCE`). It is rounded up to a multiple of 64
  (`_KEPT_CANDIDATES_STEP`) and is at least 128 (`_LEAST_KEPT_CANDIDATES`).
  Greedy decoding, or a penalty whose window and top-k come to 96 tokens or
  fewer, then needs at most 128 where a draw withholds 32 tokens or fewer,
  and so never changes the stage. A stage that keeps
  more than a generation needs stays, so that a change in what is withheld,
  or one request with other sampling, leaves the stage as it was. Every draw is the one the whole
  vocabulary gives, except between two tokens whose logits are exactly equal,
  which the device may hand over in the other order.
- Where no such count exists (`top_k` off, a penalty that raises a logit) or
  it reaches the vocabulary's size, the stage is removed and the draws are
  made from every logit, as before.
- The protocol's optional `prepare_draws` is called with a generation's
  sampling and how many tokens it may withhold before its request is
  decoded, so that a stage it changes is in place for that decode, and
  again before it draws. Where the request was decoded already, as a
  question written with its generation prompt by an earlier action, and the
  stage changes, the newest decode's candidates no longer serve and the
  prompt's last token is decoded again; a cache that cannot cut goes back to
  the newest state saved before it and decodes from there. Decoding that one token alone gave
  logits slightly different from decoding it with the rest of the prompt,
  enough to change a seeded reply. The wrapper also calls it once at load
  with the configured sampling, so that a reply under it changes the stage
  only where it withholds more tokens than that count leaves room for. For
  example, a `top_k` of 150 with 43 tokens withheld needs 193, against the
  192 kept at load.
- Changing the stage makes the engine plan its graph again (about 20 ms). Where
  the cache holds nothing, emptied with nothing decoded or restored since, as
  at load, the context warms up again (0016), so that this happens at load
  and not before the first word. A cache that holds tokens is never warmed
  up, since the warm-up empties it.
- An engine that refuses the stage is not asked again; the draws are then
  made from every logit.
- The stage is freed after the engine context that holds it.

## Consequences

Measured on 2026-11-22 on an RTX 3090 through the library, 300-token replies
to three questions, two runs each, greedy and seeded, the processor's draws
against the device's candidates:

| Model, CUDA graphs | Processor's draws | Device's candidates | Gain |
|---|---|---|---|
| Gemma 4 E2B, graphs off | 197.8 tok/s (195.2 to 199.5) | 213.8 tok/s (212.9 to 215.6) | 8.1 percent |
| Gemma 4 E2B, graphs on | 234.0 tok/s (230.5 to 236.1) | 259.2 tok/s (258.7 to 260.1) | 10.8 percent |
| Gemma 4 26B A4B, graphs off | 111.2 tok/s (110.7 to 112.0) | 116.3 tok/s (115.6 to 117.1) | 4.6 percent |
| Gemma 4 26B A4B, graphs on | 125.2 tok/s (124.4 to 125.5) | 131.1 tok/s (131.0 to 132.2) | 4.7 percent |

Medians of 24 replies each, from two processes, context 8192, the 26B with a q8_0 cache, flash
attention and the compact window cache. "Graphs on" ran with
`GGML_CUDA_GRAPH_OPT=1`, "graphs off" with `GGML_CUDA_DISABLE_GRAPHS=1`. The
wait for the first word was the same within 1 ms either way.

- Greedy and seeded replies were the same text, token for token, either way.
- When the stage was changed only after the request was decoded, a reply
  with a repetition penalty of 1.2 over 32 tokens, which needed 128 tokens
  where the stage kept 64, differed from the processor's draws on 8 of the 30
  model files the real-model tests ran on 2026-11-22 (LFM 3, Ling 3,
  Nemotron H, Qwen 3, Qwen 3.8 and a fine-tune of it, Spark X2.5 and X2.6);
  on LFM 3 the seeded story was the same for 108 characters. This is why the
  stage is changed before the request is decoded and keeps at least 128.
- With `top_k` off, top-p alone sorts the whole vocabulary on the processor:
  measured on 2026-11-21, 2.06 ms per token on a 262,144-token vocabulary
  against 0.33 ms with a top-k of 64, about 45 percent more time per token on
  Gemma 4 E2B on the GPU.

## Alternatives rejected

- The whole chain on the device, measured with
  plain llama-cpp-python at 8 percent more tokens per second on Gemma 4 E2B
  and 4 percent on the 26B: the logits never reach the host, so a token that
  may not end the turn yet could not be drawn again, and a chain whose
  withheld tokens or penalties change would be attached again, each time
  planning the engine's graph again (about 20 ms).
- Attaching a stage per generation: the same planning cost before every
  first token.
