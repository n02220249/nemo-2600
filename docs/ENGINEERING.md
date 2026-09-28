# Engineering Method

Reliability is a meta-goal of NeMo.

```text
idea -> NeMo source -> compile -> validate -> ROM -> Stella -> observe -> isolate failure -> smallest targeted fix -> regression test -> lock checkpoint
```

## Lessons

1. A malformed absolute fixup can crash a correct design if it overwrites the opcode instead of only the operand.
2. The 6507 stack must be initialized before subroutine calls and returns.
3. Branch targets must land on opcode boundaries.
4. A ROM can run without crashing while still implementing the wrong behavior.
5. The v0.6.4 correction restored the full 128-value TIA hue/luminance space after an earlier 8-entry abstraction mismatch.
6. Scanline timing, TIA registers, RIOT input, and ROM layout remain visible in the language.

Known-good checkpoints are not casually reopened. New work builds forward; regressions are isolated to the layer that changed.
