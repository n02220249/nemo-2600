# NeMo Language Guide

NeMo is deliberately between shader-like programming and low-level machine description. It lets us discuss behavior in concepts while keeping the hardware visible.

## Machine

```text
machine Atari2600
    cpu 6507
    video TIA
    io RIOT
    television NTSC
    visible_scanlines 192
```

## State

```text
state
    phase : byte = 0
```

## Functions

```text
function tia_color(index):
    hue   = index >> 3
    light = index & 7
    return (hue << 4) | (light << 1)
```

Functions may be built from other functions. The compiler should resolve dependencies coherently rather than forcing the user to manually manage low-level implementation details.

## Kernels

```text
kernel RainbowScreen:
    for scanline in 0..191:
        wait_for_scanline()
        color = rainbow_color(scanline)
        TIA.background = color
```

`wait_for_scanline()` represents a hardware synchronization requirement.

## Inputs

The tested P0 abstraction is `P0.up`, `P0.down`, `P0.left`, and `P0.right`, mapped to active-low RIOT `SWCHA` joystick bits. WASD is a host/emulator mapping, not a ROM-level input concept.

The language specification is intentionally allowed to evolve as hardware understanding improves.
