# NeMo

**NeMo is a hardware-aware programming language and compiler for Atari 2600 homebrew development.**

NeMo is a shared design medium between high-level, shader-like thinking and the Atari's real hardware: the 6507 CPU, TIA video hardware, RIOT I/O/RAM, scanline timing, registers, and ROM layout.

The goal is simple:

```text
game idea
   ↓
NeMo source (.nm)
   ↓
nemo program.nm
   ↓
validated Atari 2600 ROM (.bin)
```

You should be able to describe behavior without hand-writing 6507 assembly. The compiler owns the low-level translation, address/linker work, and validation.

> **Current status:** NeMo Compiler v0.1 is an experimental working prototype. Its supported subset is deliberately small and is anchored to tested v0.6.4 rainbow and v0.7 joystick-input programs.

## Quick start

Requirements:

- Python 3
- a text editor
- Stella for Atari 2600 testing

Compile a program:

```bash
./bin/nemo examples/rainbow_v0.6.4.nm
```

This produces:

```text
examples/rainbow_v0.6.4.bin
```

Use the simpler eventual CLI form once installed/exposed on your PATH:

```bash
nemo rainbow.nm
```

Validate without writing a ROM:

```bash
./bin/nemo examples/rainbow_v0.6.4.nm --check
```

Inspect a build:

```bash
./bin/nemo examples/rainbow_v0.6.4.nm --report
```

Emit the diagnostic backend representation:

```bash
./bin/nemo examples/rainbow_v0.6.4.nm --asm build/rainbow.asm
```

Run the regression tests:

```bash
python3 tests/run_tests.py
```

## NeMo source

Use the `.nm` extension.

A current program looks like:

```text
NeMo v0.6.4
machine Atari2600
    cpu 6507
    video TIA
    io RIOT

    television NTSC
    visible_scanlines 192

state
    phase : byte = 0

function rainbow_color(scanline):
    index = floor(scanline * 128 / 192)
    return TIA128[index]

kernel RainbowScreen:
    for scanline in 0..191:
        wait_for_scanline()
        color = rainbow_color(scanline)
        TIA.background = color

frame:
    sync()
    blank()
    RainbowScreen
    overscan()

main:
    forever:
        frame()
```

The language is intentionally allowed to evolve. Early abstractions are useful models, not dogma: as we learn more about the Atari hardware, the language and compiler model can be revised without throwing away higher-level game concepts.

See:

- [Getting Started](docs/GETTING_STARTED.md)
- [Language Guide](docs/LANGUAGE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Compiler](COMPILER.md)

## Hardware model

NeMo keeps the important Atari components explicit:

- **6507:** program execution and hardware polling
- **TIA:** video generation, scanline synchronization, color/graphics registers, and several inputs
- **RIOT:** RAM, timer, and controller/console I/O
- **scanline timing:** a first-class part of video-program behavior

For the validated joystick path, NeMo exposes:

```text
P0.up
P0.down
P0.left
P0.right
```

The ROM reads the corresponding RIOT `SWCHA` input bits. Host keyboard mappings such as WASD are external to the ROM (for example, Stella key/event mappings).

NeMo may model raw hardware concepts more abstractly at first—for example, as sampled input channels—and refine those abstractions as hardware understanding improves.

## Proven checkpoints

| Checkpoint | Result |
|---|---|
| v0.5 | scanline-aware static rainbow experiment |
| v0.6.2 | crash fixes: stack setup + correct operand-only JMP/JSR fixups |
| v0.6.3 | static rainbow behavior restored |
| v0.6.4 | **full 128-color TIA rainbow — tested and working in Stella** |
| v0.7 | **P0 joystick input through RIOT — tested and working in Stella** |
| Compiler v0.1 | **.nm → .bin compiler with regression validation** |

See [docs/CHECKPOINTS.md](docs/CHECKPOINTS.md).

## Engineering philosophy

Reliability is a first-class goal.

The project follows this loop:

```text
idea
  ↓
NeMo source
  ↓
compile
  ↓
validate
  ↓
ROM
  ↓
Stella / hardware
  ↓
observe
  ↓
identify the failing layer
  ↓
make the smallest targeted change
  ↓
regression test
  ↓
lock checkpoint
```

Known failure modes should become compiler checks. Working layers should be preserved instead of rewritten unnecessarily.

Important lessons already encoded into the project include:

- initialize the 6507 stack before using JSR/RTS
- absolute JMP/JSR fixups patch operand bytes only; never overwrite the opcode
- control-flow targets must land on opcode boundaries
- valid machine code is not enough; runtime behavior must match the NeMo semantics
- the hardware model must remain faithful enough not to erase important Atari capabilities

See [docs/ENGINEERING.md](docs/ENGINEERING.md).

## Byte identity vs. correctness

The long-term requirement is **semantic and behavioral stability**, not byte-for-byte reproduction of historical ROMs.

The priority is:

```text
same intended NeMo meaning
        ↓
valid stable Atari behavior
        ↓
validated binary
```

Compiler v0.1 currently uses exact ROM hashes for its two known fixtures because byte identity is a useful regression signal. Future compiler versions may generate different bytes while remaining correct.

## Repository layout

```text
nemo-2600/
├── README.md
├── LICENSE
├── COMPILER.md
├── CHANGELOG.md
├── VERSION.txt
├── docs/
├── examples/
├── src/
├── nemo.py
├── bin/
├── dist/
├── tests/
└── artifacts/
```

The repository includes the compiler, public documentation, examples, regression tests, and the tested historical checkpoints.

## Project goal

NeMo is intended to make Atari 2600 homebrew development easier to reason about without hiding the machine.

The human should be able to think in concepts and build new functions on the fly. The compiler should maintain coherent dependencies and handle the low-level implementation. When something breaks, the failure should improve the compiler rather than force the whole project back to trial and error.

## License

NeMo is released under the MIT License. See [LICENSE](LICENSE).
