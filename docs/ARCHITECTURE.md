# Architecture

```text
NeMo source
   -> semantic model
   -> hardware-aware IR
   -> 6507 / TIA / RIOT lowering
   -> fixups and vectors
   -> ROM image
   -> static validation
   -> Stella / Atari 2600
```

The semantic layer and binary backend are related but distinct. The user should be able to design functions without manually choosing every opcode, while the compiler retains enough hardware knowledge to make the abstraction trustworthy.

The proven checkpoints use a 4 KiB NTSC ROM model. Address calculations, branches, absolute fixups, vectors, and opcode boundaries are correctness constraints.
