# NeMo Compiler

The compiler is the bridge between readable NeMo source and a valid Atari 2600 ROM. It is hardware-aware: lowering must account for the 6507, TIA, RIOT, ROM layout, branch targets, vectors, and scanline timing.

## Intended CLI

```bash
nemo rainbow.nm
nemo rainbow.nm --check
nemo rainbow.nm --report
nemo rainbow.nm --asm build/rainbow.asm
nemo rainbow.nm -o build/rainbow.bin
```

## Pipeline

```text
.nm source -> parser -> semantic model -> hardware-aware lowering -> 6507 code -> fixups/linking -> ROM -> validation
```

## Reliability requirements

- initialize the 6507 stack before `JSR`/`RTS`
- patch absolute-address fixup operands without overwriting their opcode
- require branch targets to resolve to opcode boundaries
- validate ROM size and reset vectors
- validate timing-sensitive scanline structures
- compare generated behavior against NeMo semantics
- retain known-good fixtures as regression tests

Different compiler versions may legitimately emit different bytes. Correctness means valid, stable behavior matching the intended NeMo program.
